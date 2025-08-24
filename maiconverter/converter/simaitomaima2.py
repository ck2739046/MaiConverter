from typing import List, Tuple, Optional

from ..maima2 import (
    MaiMa2,
    BPM,
    HoldNote as Ma2HoldNote,
    TouchHoldNote as Ma2TouchHoldNote,
    SlideNote as Ma2SlideNote,
)
from ..simai import (
    SimaiChart,
    pattern_to_int,
    TapNote,
    HoldNote,
    SlideNote,
    TouchHoldNote,
    TouchTapNote,
    illegal_v_slide_exception,
    convert_v_slide_to_connected_slides,
)
from ..event import SimaiNote, NoteType


def simai_to_ma2(simai: SimaiChart, fes_mode: bool = False) -> MaiMa2:
    ma2 = MaiMa2(fes_mode=fes_mode)

    for bpm in simai.bpms:
        measure = 0.0 if bpm.measure <= 1.0 else bpm.measure

        ma2.set_bpm(measure, bpm.bpm)

    ma2.set_meter(0.0, 4, 4)
    convert_notes(ma2, simai.notes)

    if len(ma2.bpms) != 1:
        fix_durations(ma2)

    return ma2


def convert_notes(ma2: MaiMa2, simai_notes: List[SimaiNote]) -> None:
    for simai_note in simai_notes:
        note_type = simai_note.note_type
        if isinstance(simai_note, TapNote):
            is_break = note_type in [NoteType.break_tap, NoteType.break_star, NoteType.ex_break_star,
                                     NoteType.ex_break_tap]
            is_ex = note_type in [NoteType.ex_tap, NoteType.ex_star, NoteType.ex_break_star, NoteType.ex_break_tap]
            is_star = note_type in [
                NoteType.star,
                NoteType.break_star,
                NoteType.ex_star,
                NoteType.ex_break_star
            ]
            ma2.add_tap(
                measure=simai_note.measure,
                position=simai_note.position,
                is_break=is_break,
                is_star=is_star,
                is_ex=is_ex,
            )
        elif isinstance(simai_note, HoldNote):
            is_break = note_type in [NoteType.break_hold, NoteType.ex_break_hold]
            is_ex = note_type in [NoteType.ex_hold, NoteType.ex_break_hold]
            ma2.add_hold(
                measure=simai_note.measure,
                position=simai_note.position,
                duration=simai_note.duration,
                is_ex=is_ex,
                is_break=is_break
            )
        elif isinstance(simai_note, SlideNote):
            # Ma2 slide durations does not include the delay
            # like in simai
            try:
                pattern = pattern_to_int(simai_note)
                ma2.add_slide(
                    measure=simai_note.measure,
                    start_position=simai_note.position,
                    end_position=simai_note.end_position,
                    duration=simai_note.duration,
                    pattern=pattern,
                    delay=simai_note.delay,
                    is_break=simai_note.is_break,
                    is_ex=simai_note.is_ex,
                    is_connect=simai_note.is_connect
                )
            except illegal_v_slide_exception:
                # 将非法V型滑条分解为两个连接的直线滑条
                first_slide, second_slide = convert_v_slide_to_connected_slides(simai_note)
                
                # 添加第一个滑条
                pattern1 = pattern_to_int(first_slide)
                ma2.add_slide(
                    measure=first_slide.measure,
                    start_position=first_slide.position,
                    end_position=first_slide.end_position,
                    duration=first_slide.duration,
                    pattern=pattern1,
                    delay=first_slide.delay,
                    is_break=first_slide.is_break,
                    is_ex=first_slide.is_ex,
                    is_connect=first_slide.is_connect
                )
                
                # 添加第二个滑条
                pattern2 = pattern_to_int(second_slide)
                ma2.add_slide(
                    measure=second_slide.measure,
                    start_position=second_slide.position,
                    end_position=second_slide.end_position,
                    duration=second_slide.duration,
                    pattern=pattern2,
                    delay=second_slide.delay,
                    is_break=second_slide.is_break,
                    is_ex=second_slide.is_ex,
                    is_connect=second_slide.is_connect
                )
                
                print(f"Converted illegal V-slide {simai_note.position+1}-{simai_note.reflect_position+1}-{simai_note.end_position+1}")

        elif isinstance(simai_note, TouchTapNote):
            ma2.add_touch_tap(
                measure=simai_note.measure,
                position=simai_note.position,
                region=simai_note.region,
                is_firework=simai_note.is_firework,
            )
        elif isinstance(simai_note, TouchHoldNote):
            ma2.add_touch_hold(
                measure=simai_note.measure,
                position=simai_note.position,
                region=simai_note.region,
                duration=simai_note.duration,
                is_firework=simai_note.is_firework,
            )
        else:
            print(f"Warning: Unknown note type {note_type}")


def fix_durations(ma2: MaiMa2):
    """Simai note durations (slide delay, slide duration, hold note duration)
    disregards bpm changes midway, unlike ma2. So we'll have to compensate for those.
    """

    def bpm_changes(start: float, duration: float) -> List[BPM]:
        result: List[BPM] = []
        for bpm in ma2.bpms:
            if start < bpm.measure < start + duration:
                result.append(bpm)

        return result

    def compensate_duration(
            start: float, duration: float, base_bpm: float, changes: List[BPM]
    ) -> float:
        new_duration = 0

        note_start = start
        for bpm in changes:
            new_duration += (
                    ma2.get_bpm(bpm.measure - 0.0001)
                    * (bpm.measure - note_start)
                    / base_bpm
            )

            note_start = bpm.measure

        if note_start < start + duration:
            new_duration += (
                    ma2.get_bpm(note_start + 0.0001)
                    * (start + duration - note_start)
                    / base_bpm
            )

        return new_duration

    for note in ma2.notes:
        if isinstance(note, (Ma2HoldNote, Ma2TouchHoldNote, Ma2SlideNote)):
            bpms = bpm_changes(note.measure, note.duration)
            if len(bpms) != 0:
                note.duration = compensate_duration(
                    note.measure, note.duration, ma2.get_bpm(note.measure), bpms
                )
        if isinstance(note, Ma2SlideNote):
            bpms = bpm_changes(note.measure, note.delay)
            if len(bpms) != 0:
                note.delay = compensate_duration(
                    note.measure, note.delay, ma2.get_bpm(note.measure), bpms
                )
