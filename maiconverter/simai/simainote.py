from typing import Optional, Tuple

from ..event import Event, EventType, SimaiNote, NoteType
from ..tool import slide_distance, slide_is_cw

# For straightforward slide pattern conversion from simai to sxt/ma2.
# Use simai_pattern_to_int to cover all simai slide patterns.
slide_dict = {
    "-": 1,
    "p": 4,
    "q": 5,
    "s": 6,
    "z": 7,
    "v": 8,
    "pp": 9,
    "qq": 10,
    "w": 13,
}

slide_patterns = [
    "-",
    "^",
    ">",
    "<",
    "p",
    "q",
    "s",
    "z",
    "v",
    "pp",
    "qq",
    "V",
    "w",
]


class TapNote(SimaiNote):
    def __init__(
            self,
            measure: float,
            position: int,
            is_break: bool = False,
            is_star: bool = False,
            is_ex: bool = False,
    ) -> None:
        measure = round(100000.0 * measure) / 100000.0

        if is_star:
            if is_ex and is_break:
                super().__init__(measure, position, NoteType.ex_break_star)
            elif is_ex:
                super().__init__(measure, position, NoteType.ex_star)
            elif is_break:
                super().__init__(measure, position, NoteType.break_star)
            else:
                super().__init__(measure, position, NoteType.star)
        else:
            if is_ex and is_break:
                super().__init__(measure, position, NoteType.ex_break_tap)
            elif is_ex:
                super().__init__(measure, position, NoteType.ex_tap)
            elif is_break:
                super().__init__(measure, position, NoteType.break_tap)
            else:
                super().__init__(measure, position, NoteType.tap)


class HoldNote(SimaiNote):
    def __init__(
            self, measure: float, position: int, duration: float, is_ex: bool = False, is_break: bool = False
    ) -> None:
        if duration < 0:
            raise ValueError(f"Hold duration is negative: {duration}")

        measure = round(100000.0 * measure) / 100000.0
        duration = round(100000.0 * duration) / 100000.0
        if is_ex and is_break:
            super().__init__(measure, position, NoteType.ex_break_hold)
        elif is_ex:
            super().__init__(measure, position, NoteType.ex_hold)
        elif is_break:
            super().__init__(measure, position, NoteType.break_hold)
        else:
            super().__init__(measure, position, NoteType.hold)

        self.duration = duration


class SlideNote(SimaiNote):
    def __init__(
            self,
            measure: float,
            start_position: int,
            end_position: int,
            duration: float,
            pattern: str,
            delay: float = 0.25,
            is_break: bool = False,
            is_ex: bool = False,
            is_connect: bool = False,
            reflect_position: Optional[int] = None,
    ) -> None:
        """Produces a simai slide note.

        Note: Simai slide durations does not include slide delay.

        Args:
            measure (float): Measure where the slide note begins.
            start_position (int): Button where slide begins. [0, 7]
            end_position (int): Button where slide ends. [0, 7]
            duration (float): Total duration, in measures, of
                the slide, including delay.
            pattern (str): Simai slide pattern. If 'V', then
                reflect_position should not be None.
            delay (float, optional): Time duration, in measures,
                from where slide appears and when it starts to move.
                Defaults to 0.25.
            reflect_position (Optional[int], optional): For 'V'
                patterns. Defaults to None.

        Raises:
            ValueError: When duration is not positive
                or when delay is negative
        """
        measure = round(100000.0 * measure) / 100000.0
        duration = round(100000.0 * duration) / 100000.0
        delay = round(100000.0 * delay) / 100000.0
        if duration <= 0:
            raise ValueError("Duration is not positive " + str(duration))
        if delay < 0:
            raise ValueError("Delay is negative " + str(duration))
        if pattern not in slide_patterns:
            raise ValueError("Unknown slide pattern " + str(pattern))
        if pattern == "V" and reflect_position is None:
            raise Exception("Slide pattern 'V' is given " + "without reflection point")

        super().__init__(measure, start_position, NoteType.complete_slide)
        self.duration = duration
        self.end_position = end_position
        self.pattern = pattern
        self.delay = delay
        self.is_break = is_break
        self.is_ex = is_ex
        self.is_connect = is_connect
        self.reflect_position = reflect_position


class TouchTapNote(SimaiNote):
    def __init__(
            self, measure: float, position: int, region: str, is_firework: bool = False
    ) -> None:
        measure = round(measure * 100000.0) / 100000.0

        super().__init__(measure, position, NoteType.touch_tap)
        self.is_firework = is_firework
        self.region = region


class TouchHoldNote(SimaiNote):
    def __init__(
            self,
            measure: float,
            position: int,
            region: str,
            duration: float,
            is_firework: bool = False,
    ) -> None:
        measure = round(measure * 100000.0) / 100000.0
        duration = round(duration * 100000.0) / 100000.0

        super().__init__(measure, position, NoteType.touch_hold)
        self.is_firework = is_firework
        self.region = region
        self.duration = duration


class BPM(Event):
    def __init__(self, measure: float, bpm: float) -> None:
        if bpm <= 0:
            raise ValueError("BPM is not positive " + str(bpm))

        measure = round(measure * 100000.0) / 100000.0

        super().__init__(measure, EventType.bpm)
        self.bpm = bpm


def slide_to_pattern_str(slide_note: SlideNote) -> str:
    pattern = slide_note.pattern
    if pattern != "V":
        return pattern

    if slide_note.reflect_position is None:
        raise Exception("Slide has 'V' pattern but no reflect position")

    return "V{}".format(slide_note.reflect_position + 1)


def pattern_from_int(
        pattern: int, start_position: int, end_position: int
) -> Tuple[str, Optional[int]]:
    top_list = [0, 1, 6, 7]
    inv_slide_dict = {v: k for k, v in slide_dict.items()}
    dict_result = inv_slide_dict.get(pattern)
    if dict_result is not None:
        return dict_result, None
    if pattern in [2, 3]:
        # Have I told you how much I hate the simai format?
        is_cw = pattern == 3
        distance = slide_distance(start_position, end_position, is_cw)
        if 0 < distance <= 3:
            return "^", None
        if distance == 0:
            if start_position in top_list and is_cw:
                return ">", None
            if start_position in top_list and not is_cw:
                return "<", None
            if start_position not in top_list and is_cw:
                return "<", None

            return ">", None
        if (start_position in top_list and is_cw) or not (
                start_position in top_list or is_cw
        ):
            return ">", None

        return "<", None
    if pattern in [11, 12]:
        if pattern == 11:
            reflect_position = start_position - 2
            if reflect_position < 0:
                reflect_position += 8
        else:
            reflect_position = start_position + 2
            if reflect_position > 7:
                reflect_position -= 8

        return "V", reflect_position

    raise ValueError(f"Unknown pattern: {pattern}")


def is_v_slide_180_degree(slide_note: SlideNote) -> bool:
    if slide_note.pattern != "V" or slide_note.reflect_position is None:
        return False
    
    diff = abs(slide_note.reflect_position - slide_note.position)
    return diff == 4


def convert_v_slide_to_connected_slides(slide_note: SlideNote) -> Tuple[SlideNote, SlideNote]:
    """将V型180度角滑条转换为两个连接的直线滑条"""
    if not is_v_slide_180_degree(slide_note):
        raise ValueError("Only V slides with 180 degree angles can be converted")
    
    # 第一个滑条：从起始位置到反射位置
    first_slide = SlideNote(
        measure=slide_note.measure,
        start_position=slide_note.position,
        end_position=slide_note.reflect_position,
        duration=slide_note.duration / 2,  # 平分时长
        pattern="-",  # 直线滑条
        delay=slide_note.delay,
        is_break=slide_note.is_break,
        is_ex=slide_note.is_ex,
        is_connect=slide_note.is_connect  # 原始连接状态
    )
    
    # 第二个滑条：从反射位置到结束位置
    # 时间计算：起始时间 + delay + 第一个滑条的duration
    second_slide = SlideNote(
        measure=slide_note.measure + slide_note.delay + slide_note.duration / 2,
        start_position=slide_note.reflect_position,
        end_position=slide_note.end_position,
        duration=slide_note.duration / 2,  # 平分时长
        pattern="-",  # 直线滑条
        delay=0,  # 连接滑条没有延迟
        is_break=slide_note.is_break,
        is_ex=slide_note.is_ex,
        is_connect=True  # 第二个滑条总是连接滑条
    )
    
    return first_slide, second_slide


class VSlide180DegreeException(Exception):
    def __init__(self, slide_note: SlideNote):
        self.slide_note = slide_note
        super().__init__(f"V slide with 180 degree angle should be converted to connected straight slides")


def pattern_to_int(slide_note: SlideNote) -> int:
    pattern = slide_note.pattern
    top_list = [0, 1, 6, 7]

    dict_result = slide_dict.get(pattern)
    if dict_result is not None:
        return dict_result
    elif pattern == "^":
        is_cw = slide_is_cw(slide_note.position, slide_note.end_position, pattern)
        if is_cw:
            return 3
        else:
            return 2
    elif pattern == ">":
        is_top = slide_note.position in top_list
        if is_top:
            return 3
        else:
            return 2
    elif pattern == "<":
        is_top = slide_note.position in top_list
        if is_top:
            return 2
        else:
            return 3
    elif pattern == "V":
        if slide_note.reflect_position is None:
            raise ValueError("Slide pattern 'V' has no reflect position defined")
        
        # 检查是否为180度角情况
        if is_v_slide_180_degree(slide_note):
            raise VSlide180DegreeException(slide_note)
        
        is_cw = slide_is_cw(slide_note.position, slide_note.reflect_position, pattern)
        if is_cw:
            return 12
        else:
            return 11
    else:
        raise ValueError(f"Unknown slide pattern {pattern}")
