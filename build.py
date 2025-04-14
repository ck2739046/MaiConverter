import PyInstaller.__main__

def build():
    # Define data files to include
    data_files = [
        ("./maiconverter/simai/simai.lark", "./maiconverter/simai"),
        ("./maiconverter/simai/simai_fragment.lark", "./maiconverter/simai")
    ]
    
    # Set up PyInstaller arguments
    args = [
        '--clean',
        '--onefile',
        './maiconverter/test.py',
        '--name=maiconverter',
        '--version-file=./version.txt'
    ]
    
    # Add data files to arguments
    for src, dest in data_files:
        args.extend(['--add-data', f'{src};{dest}'])
    
    # Run PyInstaller
    PyInstaller.__main__.run(args)

if __name__ == '__main__':
    build()