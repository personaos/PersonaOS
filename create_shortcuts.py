#!/usr/bin/env python3
"""
PersonaOS Desktop Integration
Creates desktop shortcuts and system integration for easy access
"""

import os
import sys
import platform
from pathlib import Path
import subprocess

def create_windows_shortcuts():
    """Create desktop shortcuts for Windows"""
    desktop = Path.home() / "Desktop"
    if not desktop.exists():
        print("❌ Desktop directory not found")
        return False
    
    personaos_dir = Path.cwd()
    
    # PersonaOS CLI shortcut
    cli_content = f"""@echo off
title PersonaOS CLI
cd /d "{personaos_dir}"
echo Starting PersonaOS CLI...
echo.
python start.py --cli
pause"""
    
    cli_shortcut = desktop / "PersonaOS CLI.bat"
    with open(cli_shortcut, 'w') as f:
        f.write(cli_content)
    
    # PersonaOS Web UI shortcut  
    webui_content = f"""@echo off
title PersonaOS Web UI
cd /d "{personaos_dir}"
echo Starting PersonaOS Web UI...
echo This will open your browser automatically.
echo.
python start.py --web
pause"""
    
    webui_shortcut = desktop / "PersonaOS Web UI.bat"
    with open(webui_shortcut, 'w') as f:
        f.write(webui_content)
    
    # PersonaOS Launcher shortcut
    launcher_content = f"""@echo off  
title PersonaOS Launcher
cd /d "{personaos_dir}"
echo Welcome to PersonaOS!
echo.
python start.py
pause"""
    
    launcher_shortcut = desktop / "PersonaOS.bat"
    with open(launcher_shortcut, 'w') as f:
        f.write(launcher_content)
    
    # System Health Check shortcut
    health_content = f"""@echo off
title PersonaOS Health Check
cd /d "{personaos_dir}"
echo Running PersonaOS system health check...
echo.
python system_health.py --verbose
echo.
pause"""
    
    health_shortcut = desktop / "PersonaOS Health Check.bat"
    with open(health_shortcut, 'w') as f:
        f.write(health_content)
    
    print("✅ Windows desktop shortcuts created:")
    print(f"  • {cli_shortcut}")
    print(f"  • {webui_shortcut}")
    print(f"  • {launcher_shortcut}")
    print(f"  • {health_shortcut}")
    
    return True

def create_linux_shortcuts():
    """Create desktop shortcuts for Linux"""
    desktop = Path.home() / "Desktop"
    applications = Path.home() / ".local/share/applications"
    
    # Ensure directories exist
    desktop.mkdir(exist_ok=True)
    applications.mkdir(parents=True, exist_ok=True)
    
    personaos_dir = Path.cwd()
    python_path = sys.executable
    
    shortcuts = {
        "PersonaOS": {
            "name": "PersonaOS",
            "comment": "PersonaOS AI Assistant Launcher",
            "exec": f"{python_path} {personaos_dir}/start.py",
            "icon": f"{personaos_dir}/assets/icon.png",
            "categories": "Development;Science;Education;"
        },
        "PersonaOS-CLI": { 
            "name": "PersonaOS CLI",
            "comment": "PersonaOS Command Line Interface",
            "exec": f"gnome-terminal -- {python_path} {personaos_dir}/start.py --cli",
            "icon": f"{personaos_dir}/assets/icon-cli.png",
            "categories": "Development;System;TerminalEmulator;"
        },
        "PersonaOS-WebUI": {
            "name": "PersonaOS Web UI",
            "comment": "PersonaOS Web Interface",
            "exec": f"{python_path} {personaos_dir}/start.py --web",
            "icon": f"{personaos_dir}/assets/icon-web.png", 
            "categories": "Development;Science;WebBrowser;"
        }
    }
    
    created_files = []
    
    for key, shortcut in shortcuts.items():
        desktop_file_content = f"""[Desktop Entry]
Version=1.0
Type=Application
Name={shortcut['name']}
Comment={shortcut['comment']}
Exec={shortcut['exec']}
Icon={shortcut['icon']}
Categories={shortcut['categories']}
Terminal=false
StartupNotify=true
"""
        
        # Create desktop shortcut
        desktop_file = desktop / f"{key}.desktop"
        with open(desktop_file, 'w') as f:
            f.write(desktop_file_content)
        
        # Make executable
        os.chmod(desktop_file, 0o755)
        created_files.append(desktop_file)
        
        # Create applications menu entry
        app_file = applications / f"{key}.desktop"
        with open(app_file, 'w') as f:
            f.write(desktop_file_content)
        
        created_files.append(app_file)
    
    print("✅ Linux desktop shortcuts created:")
    for file in created_files:
        print(f"  • {file}")
    
    return True

def create_macos_shortcuts():
    """Create shortcuts for macOS"""
    applications = Path("/Applications")
    personaos_dir = Path.cwd()
    python_path = sys.executable
    
    # Create simple shell scripts that can be run
    scripts_dir = personaos_dir / "macos_launchers"
    scripts_dir.mkdir(exist_ok=True)
    
    shortcuts = {
        "PersonaOS": f'#!/bin/bash\ncd "{personaos_dir}"\n{python_path} start.py\n',
        "PersonaOS-CLI": f'#!/bin/bash\ncd "{personaos_dir}"\n{python_path} start.py --cli\n',
        "PersonaOS-WebUI": f'#!/bin/bash\ncd "{personaos_dir}"\n{python_path} start.py --web\n'
    }
    
    created_files = []
    
    for name, content in shortcuts.items():
        script_file = scripts_dir / f"{name}.command"
        with open(script_file, 'w') as f:
            f.write(content)
        
        # Make executable
        os.chmod(script_file, 0o755)
        created_files.append(script_file)
    
    print("✅ macOS launcher scripts created:")
    for file in created_files:
        print(f"  • {file}")
    
    print("\n💡 To add to Dock:")
    print("  1. Open Finder and navigate to the PersonaOS directory")
    print("  2. Go to macos_launchers folder")
    print("  3. Drag .command files to your Dock")
    
    return True

def create_start_menu_entry():
    """Create Windows Start Menu entry"""
    if platform.system().lower() != "windows":
        return False
    
    try:
        start_menu = Path.home() / "AppData/Roaming/Microsoft/Windows/Start Menu/Programs"
        personaos_folder = start_menu / "PersonaOS"
        personaos_folder.mkdir(exist_ok=True)
        
        personaos_dir = Path.cwd()
        
        # Main launcher
        main_shortcut = personaos_folder / "PersonaOS.bat"
        with open(main_shortcut, 'w') as f:
            f.write(f'''@echo off
cd /d "{personaos_dir}"
python start.py''')
        
        # CLI shortcut
        cli_shortcut = personaos_folder / "PersonaOS CLI.bat"
        with open(cli_shortcut, 'w') as f:
            f.write(f'''@echo off
cd /d "{personaos_dir}"
python start.py --cli''')
        
        # Web UI shortcut
        web_shortcut = personaos_folder / "PersonaOS Web UI.bat"
        with open(web_shortcut, 'w') as f:
            f.write(f'''@echo off
cd /d "{personaos_dir}"
python start.py --web''')
        
        print("✅ Windows Start Menu entries created:")
        print(f"  • {personaos_folder}")
        return True
        
    except Exception as e:
        print(f"❌ Failed to create Start Menu entries: {e}")
        return False

def create_system_path_entry():
    """Add PersonaOS to system PATH (optional)"""
    personaos_dir = Path.cwd()
    system = platform.system().lower()
    
    if system == "windows":
        print("\n💡 To add PersonaOS to system PATH (optional):")
        print("  1. Open System Properties > Environment Variables")
        print("  2. Add to PATH variable:")
        print(f"     {personaos_dir}")
        print("  3. You can then run 'python start.py' from anywhere")
        
    elif system in ["linux", "darwin"]:
        shell_config = Path.home() / ".bashrc"
        if Path.home() / ".zshrc" in [Path.home() / ".zshrc"]:
            shell_config = Path.home() / ".zshrc"
        
        print(f"\n💡 To add PersonaOS to system PATH (optional):")
        print(f"  Add to {shell_config}:")
        print(f"    export PATH=\"{personaos_dir}:$PATH\"")
        print(f"    alias personaos=\"python {personaos_dir}/start.py\"")
        print("  Then run: source ~/.bashrc (or ~/.zshrc)")

def main():
    """Create desktop integration based on the operating system"""
    print("🔧 Creating PersonaOS desktop integration...")
    
    system = platform.system().lower()
    success = False
    
    if system == "windows":
        print("\n📱 Creating Windows shortcuts...")
        success = create_windows_shortcuts()
        create_start_menu_entry()
        
    elif system == "linux":
        print("\n🐧 Creating Linux shortcuts...")
        success = create_linux_shortcuts()
        
    elif system == "darwin":
        print("\n🍎 Creating macOS shortcuts...")  
        success = create_macos_shortcuts()
        
    else:
        print(f"❌ Unsupported operating system: {system}")
        return False
    
    if success:
        print("\n✅ Desktop integration created successfully!")
        create_system_path_entry()
        
        print("\n🚀 You can now start PersonaOS from:")
        print("  • Desktop shortcuts")
        if system == "windows":
            print("  • Start Menu > PersonaOS")
        elif system == "linux":
            print("  • Applications menu")
        print("  • Command line: python start.py")
        
        return True
    else:
        print("❌ Failed to create desktop integration")
        return False

if __name__ == "__main__":
    main()