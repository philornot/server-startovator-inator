"""
Minecraft Server Mod Scanner
Scans and extracts information about installed mods from .jar files
"""
import json
import os
import re
import zipfile
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional


class ModInfo:
    """Information about a single mod"""

    def __init__(self, name: str, version: str = "Unknown", mod_id: str = "", file_name: str = ""):
        """Initialize mod information

        Args:
            name: Display name of the mod
            version: Version string
            mod_id: Unique mod identifier
            file_name: Original .jar filename
        """
        self.name = name
        self.version = version
        self.mod_id = mod_id
        self.file_name = file_name

    def __repr__(self):
        return f"ModInfo(name={self.name}, version={self.version}, id={self.mod_id})"

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization

        Returns:
            Dictionary representation of mod info
        """
        return {
            "name": self.name,
            "version": self.version,
            "mod_id": self.mod_id,
            "file_name": self.file_name
        }

    @staticmethod
    def from_dict(data: dict) -> 'ModInfo':
        """Create ModInfo from dictionary

        Args:
            data: Dictionary with mod information

        Returns:
            ModInfo instance
        """
        return ModInfo(
            name=data.get("name", "Unknown"),
            version=data.get("version", "Unknown"),
            mod_id=data.get("mod_id", ""),
            file_name=data.get("file_name", "")
        )


class ModScanner:
    """Scanner for Minecraft server mods directory"""

    def __init__(self, server_dir: str, cache_duration: int = 300):
        """Initialize mod scanner

        Args:
            server_dir: Path to Minecraft server directory
            cache_duration: How long to cache results in seconds (default: 5 minutes)
        """
        self.server_dir = Path(server_dir)
        self.mods_dir = self.server_dir / "mods"
        self.cache_duration = timedelta(seconds=cache_duration)
        self.cached_mods: List[ModInfo] = []
        self.last_scan_time: Optional[datetime] = None

    def _parse_fabric_mod_json(self, jar_path: Path) -> Optional[ModInfo]:
        """Parse Fabric mod metadata from fabric.mod.json

        Args:
            jar_path: Path to .jar file

        Returns:
            ModInfo if successfully parsed, None otherwise
        """
        try:
            with zipfile.ZipFile(jar_path, 'r') as jar:
                if 'fabric.mod.json' in jar.namelist():
                    with jar.open('fabric.mod.json') as f:
                        data = json.loads(f.read().decode('utf-8'))
                        return ModInfo(
                            name=data.get('name', jar_path.stem),
                            version=data.get('version', 'Unknown'),
                            mod_id=data.get('id', ''),
                            file_name=jar_path.name
                        )
        except Exception as e:
            pass
        return None

    def _parse_forge_mods_toml(self, jar_path: Path) -> Optional[ModInfo]:
        """Parse Forge mod metadata from META-INF/mods.toml

        Args:
            jar_path: Path to .jar file

        Returns:
            ModInfo if successfully parsed, None otherwise
        """
        try:
            with zipfile.ZipFile(jar_path, 'r') as jar:
                toml_path = 'META-INF/mods.toml'
                if toml_path in jar.namelist():
                    with jar.open(toml_path) as f:
                        content = f.read().decode('utf-8')

                        # Simple TOML parsing for common fields
                        mod_id = re.search(r'modId\s*=\s*["\']([^"\']+)["\']', content)
                        version = re.search(r'version\s*=\s*["\']([^"\']+)["\']', content)
                        display_name = re.search(r'displayName\s*=\s*["\']([^"\']+)["\']', content)

                        return ModInfo(
                            name=display_name.group(1) if display_name else jar_path.stem,
                            version=version.group(1) if version else 'Unknown',
                            mod_id=mod_id.group(1) if mod_id else '',
                            file_name=jar_path.name
                        )
        except Exception as e:
            pass
        return None

    def _parse_manifest(self, jar_path: Path) -> Optional[ModInfo]:
        """Parse basic jar manifest

        Args:
            jar_path: Path to .jar file

        Returns:
            ModInfo if successfully parsed, None otherwise
        """
        try:
            with zipfile.ZipFile(jar_path, 'r') as jar:
                if 'META-INF/MANIFEST.MF' in jar.namelist():
                    with jar.open('META-INF/MANIFEST.MF') as f:
                        content = f.read().decode('utf-8')

                        impl_title = re.search(r'Implementation-Title:\s*(.+)', content)
                        impl_version = re.search(r'Implementation-Version:\s*(.+)', content)

                        if impl_title:
                            return ModInfo(
                                name=impl_title.group(1).strip(),
                                version=impl_version.group(1).strip() if impl_version else 'Unknown',
                                mod_id='',
                                file_name=jar_path.name
                            )
        except Exception as e:
            pass
        return None

    def _parse_jar_file(self, jar_path: Path) -> ModInfo:
        """Try to extract mod info from jar file using multiple methods

        Args:
            jar_path: Path to .jar file

        Returns:
            ModInfo with extracted information or basic info from filename
        """
        # Try Fabric format first
        mod_info = self._parse_fabric_mod_json(jar_path)
        if mod_info:
            return mod_info

        # Try Forge format
        mod_info = self._parse_forge_mods_toml(jar_path)
        if mod_info:
            return mod_info

        # Try manifest
        mod_info = self._parse_manifest(jar_path)
        if mod_info:
            return mod_info

        # Fallback to filename
        return ModInfo(
            name=jar_path.stem,
            version='Unknown',
            mod_id='',
            file_name=jar_path.name
        )

    def scan_mods(self, force_refresh: bool = False) -> List[ModInfo]:
        """Scan mods directory and return list of installed mods

        Args:
            force_refresh: If True, ignore cache and force rescan

        Returns:
            List of ModInfo objects
        """
        # Check cache
        if not force_refresh and self.last_scan_time:
            cache_age = datetime.now() - self.last_scan_time
            if cache_age < self.cache_duration:
                return self.cached_mods

        # Check if mods directory exists
        if not self.mods_dir.exists():
            return []

        mods = []
        try:
            for file_path in self.mods_dir.glob("*.jar"):
                if file_path.is_file():
                    mod_info = self._parse_jar_file(file_path)
                    mods.append(mod_info)
        except Exception as e:
            pass

        # Sort by name
        mods.sort(key=lambda m: m.name.lower())

        # Update cache
        self.cached_mods = mods
        self.last_scan_time = datetime.now()

        return mods

    def get_mods_count(self) -> int:
        """Get count of installed mods

        Returns:
            Number of mods
        """
        return len(self.scan_mods())

    def format_mods_list(self, max_mods: int = 50) -> str:
        """Format mods list as readable string

        Args:
            max_mods: Maximum number of mods to include

        Returns:
            Formatted string with mod information
        """
        mods = self.scan_mods()

        if not mods:
            return "No mods installed"

        lines = [f"Total mods: {len(mods)}"]

        for i, mod in enumerate(mods[:max_mods]):
            lines.append(f"• {mod.name} (v{mod.version})")

        if len(mods) > max_mods:
            lines.append(f"... and {len(mods) - max_mods} more")

        return "\n".join(lines)

    def save_cache(self, cache_file: str = "mods_cache.json"):
        """Save current cache to file

        Args:
            cache_file: Path to cache file
        """
        try:
            cache_data = {
                "last_scan": self.last_scan_time.isoformat() if self.last_scan_time else None,
                "mods": [mod.to_dict() for mod in self.cached_mods]
            }
            with open(cache_file, 'w', encoding='utf-8') as f:
                json.dump(cache_data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            pass

    def load_cache(self, cache_file: str = "mods_cache.json") -> bool:
        """Load cache from file

        Args:
            cache_file: Path to cache file

        Returns:
            True if cache was loaded successfully
        """
        try:
            if not os.path.exists(cache_file):
                return False

            with open(cache_file, 'r', encoding='utf-8') as f:
                cache_data = json.load(f)

            if cache_data.get("last_scan"):
                self.last_scan_time = datetime.fromisoformat(cache_data["last_scan"])

            self.cached_mods = [
                ModInfo.from_dict(mod_data)
                for mod_data in cache_data.get("mods", [])
            ]

            return True
        except Exception as e:
            return False