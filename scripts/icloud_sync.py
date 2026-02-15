#!/usr/bin/env python3
"""
iCloud Drive Sync - Download files from iCloud Drive

This script connects to iCloud Drive and downloads files, useful for
syncing Apple Health exports from your iPhone.

Setup:
    pip install pyicloud

Usage:
    # List files in iCloud Drive root
    python scripts/icloud_sync.py --list

    # List files in a specific folder
    python scripts/icloud_sync.py --list --folder "Health Exports"

    # Download a specific file
    python scripts/icloud_sync.py --download "Health Exports/export.xml"

    # Download latest file from a folder
    python scripts/icloud_sync.py --download-latest "Health Exports" --output ./export.xml

    # Full health sync workflow
    python scripts/icloud_sync.py --health-sync

Environment Variables:
    ICLOUD_USERNAME: Your Apple ID email
    ICLOUD_PASSWORD: Your Apple ID password (or use keyring)

Workflow for Apple Health:
    1. On iPhone: Health → Export All Health Data → Save to Files → iCloud Drive/Health Exports
    2. Run: python scripts/icloud_sync.py --health-sync
    3. Script downloads export.xml and runs apple_health_to_notion.py
"""

import argparse
import os
import sys
import tempfile
import zipfile
from pathlib import Path
from shutil import copyfileobj

# Check for pyicloud
try:
    from pyicloud import PyiCloudService
except ImportError:
    print("❌ pyicloud not installed. Run: pip install pyicloud")
    sys.exit(1)


def get_credentials():
    """Get iCloud credentials from environment or prompt."""
    username = os.environ.get("ICLOUD_USERNAME")
    password = os.environ.get("ICLOUD_PASSWORD")

    if not username:
        username = input("Apple ID (email): ")
    if not password:
        import getpass
        password = getpass.getpass("Password: ")

    return username, password


def authenticate():
    """Authenticate with iCloud, handling 2FA."""
    username, password = get_credentials()

    print(f"🔐 Connecting to iCloud as {username}...")

    # Use a persistent cookie directory
    cookie_dir = Path.home() / ".pyicloud"
    cookie_dir.mkdir(exist_ok=True)

    api = PyiCloudService(username, password, cookie_directory=str(cookie_dir))

    # Handle 2FA
    if api.requires_2fa:
        print("\n📱 Two-factor authentication required.")
        print("A code has been sent to your trusted devices.")
        code = input("Enter the 6-digit code: ")

        result = api.validate_2fa_code(code)
        if not result:
            print("❌ Failed to verify code")
            sys.exit(1)

        print("✅ 2FA verified")

        # Trust session to reduce future 2FA prompts
        if not api.is_trusted_session:
            print("🔒 Requesting session trust...")
            api.trust_session()

    elif api.requires_2sa:
        # Two-step authentication (older method)
        print("\n📱 Two-step authentication required.")
        devices = api.trusted_devices
        for i, device in enumerate(devices):
            print(f"  {i}: {device.get('deviceName', 'Unknown')}")

        device_idx = int(input("Select device: "))
        device = devices[device_idx]

        if not api.send_verification_code(device):
            print("❌ Failed to send code")
            sys.exit(1)

        code = input("Enter code: ")
        if not api.validate_verification_code(device, code):
            print("❌ Failed to verify code")
            sys.exit(1)

    print("✅ Connected to iCloud")
    return api


def list_folder(api, folder_path: str = None):
    """List contents of an iCloud Drive folder."""
    drive = api.drive

    if folder_path:
        # Navigate to folder
        parts = folder_path.strip("/").split("/")
        current = drive
        for part in parts:
            if part in current:
                current = current[part]
            else:
                print(f"❌ Folder not found: {folder_path}")
                return
    else:
        current = drive

    print(f"\n📁 Contents of {'/' + folder_path if folder_path else 'iCloud Drive'}:\n")

    items = list(current.dir())
    if not items:
        print("  (empty)")
        return

    for name in sorted(items):
        item = current[name]
        item_type = getattr(item, "type", "folder")

        if item_type == "folder":
            print(f"  📁 {name}/")
        else:
            size = getattr(item, "size", 0)
            size_str = f"{size / 1024:.1f} KB" if size < 1024 * 1024 else f"{size / 1024 / 1024:.1f} MB"
            date = getattr(item, "date_modified", None)
            date_str = date.strftime("%Y-%m-%d %H:%M") if date else ""
            print(f"  📄 {name} ({size_str}) {date_str}")


def download_file(api, file_path: str, output_path: str = None):
    """Download a file from iCloud Drive."""
    drive = api.drive

    parts = file_path.strip("/").split("/")
    current = drive

    # Navigate to file
    for part in parts[:-1]:
        if part in current:
            current = current[part]
        else:
            print(f"❌ Path not found: {file_path}")
            return None

    filename = parts[-1]
    if filename not in current:
        print(f"❌ File not found: {filename}")
        return None

    file_item = current[filename]

    # Determine output path
    if not output_path:
        output_path = filename

    print(f"⬇️  Downloading {filename}...")

    with file_item.open(stream=True) as response:
        with open(output_path, "wb") as f:
            copyfileobj(response.raw, f)

    print(f"✅ Downloaded to {output_path}")
    return output_path


def download_latest(api, folder_path: str, output_path: str = None, extension: str = None):
    """Download the most recent file from a folder."""
    drive = api.drive

    # Navigate to folder
    parts = folder_path.strip("/").split("/")
    current = drive
    for part in parts:
        if part in current:
            current = current[part]
        else:
            print(f"❌ Folder not found: {folder_path}")
            return None

    # Find files
    files = []
    for name in current.dir():
        item = current[name]
        if getattr(item, "type", "folder") != "folder":
            if extension is None or name.endswith(extension):
                files.append((name, item, getattr(item, "date_modified", None)))

    if not files:
        print(f"❌ No files found in {folder_path}")
        return None

    # Sort by date (newest first)
    files.sort(key=lambda x: x[2] if x[2] else "", reverse=True)
    latest_name, latest_item, latest_date = files[0]

    print(f"📄 Latest file: {latest_name} ({latest_date})")

    # Download
    if not output_path:
        output_path = latest_name

    print(f"⬇️  Downloading...")

    with latest_item.open(stream=True) as response:
        with open(output_path, "wb") as f:
            copyfileobj(response.raw, f)

    print(f"✅ Downloaded to {output_path}")
    return output_path


def health_sync_workflow(api):
    """Full workflow: download health export and sync to Notion."""
    print("\n🏥 Apple Health Sync Workflow\n")

    # Look for health exports folder
    health_folder = "Health Exports"

    drive = api.drive
    if health_folder not in drive:
        print(f"❌ Folder '{health_folder}' not found in iCloud Drive")
        print("\n📝 To set up:")
        print("   1. Create a folder called 'Health Exports' in iCloud Drive")
        print("   2. On iPhone: Health → Export All Health Data")
        print("   3. Save to Files → iCloud Drive → Health Exports")
        return

    # Download latest zip or xml
    with tempfile.TemporaryDirectory() as tmpdir:
        # Try to find latest export
        output = download_latest(api, health_folder, extension=".zip")

        if output and output.endswith(".zip"):
            # Extract XML from zip
            print(f"📦 Extracting {output}...")
            with zipfile.ZipFile(output, "r") as zf:
                # Find export.xml in the zip
                xml_files = [f for f in zf.namelist() if f.endswith("export.xml")]
                if xml_files:
                    zf.extract(xml_files[0], tmpdir)
                    xml_path = Path(tmpdir) / xml_files[0]
                    print(f"✅ Extracted to {xml_path}")

                    # Run health sync
                    run_health_sync(str(xml_path))
                else:
                    print("❌ No export.xml found in zip")
        elif output and output.endswith(".xml"):
            run_health_sync(output)
        else:
            # Try finding .xml directly
            output = download_latest(api, health_folder, extension=".xml")
            if output:
                run_health_sync(output)
            else:
                print("❌ No health export found (.zip or .xml)")


def run_health_sync(xml_path: str):
    """Run the Apple Health to Notion sync."""
    import subprocess

    print(f"\n🔄 Syncing health data to Notion...")

    script_path = Path(__file__).parent / "apple_health_to_notion.py"

    result = subprocess.run(
        [sys.executable, str(script_path), xml_path, "--days", "30"],
        capture_output=False,
    )

    if result.returncode == 0:
        print("\n✅ Health sync complete!")
    else:
        print("\n❌ Health sync failed")


def main():
    parser = argparse.ArgumentParser(description="iCloud Drive Sync")
    parser.add_argument("--list", action="store_true", help="List folder contents")
    parser.add_argument("--folder", type=str, help="Folder path for --list")
    parser.add_argument("--download", type=str, help="Download a specific file")
    parser.add_argument("--download-latest", type=str, help="Download latest file from folder")
    parser.add_argument("--output", "-o", type=str, help="Output path for downloads")
    parser.add_argument("--extension", type=str, help="Filter by extension for --download-latest")
    parser.add_argument("--health-sync", action="store_true", help="Full health export sync workflow")

    args = parser.parse_args()

    # Authenticate
    api = authenticate()

    if args.list:
        list_folder(api, args.folder)
    elif args.download:
        download_file(api, args.download, args.output)
    elif args.download_latest:
        download_latest(api, args.download_latest, args.output, args.extension)
    elif args.health_sync:
        health_sync_workflow(api)
    else:
        # Default: list root
        list_folder(api)


if __name__ == "__main__":
    main()
