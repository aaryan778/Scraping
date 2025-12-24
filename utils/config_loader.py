"""
Configuration loader with versioning and hot-reload support
Loads and manages job categories, skills, and countries configuration
"""
import json
import os
from typing import Dict, Any, Optional
from pathlib import Path
from datetime import datetime
from loguru import logger
from dotenv import load_dotenv
import hashlib

load_dotenv()


class ConfigLoader:
    """Configuration loader with versioning and change detection"""

    def __init__(self, config_dir: str = "config"):
        """
        Initialize config loader

        Args:
            config_dir: Directory containing configuration files
        """
        self.config_dir = Path(config_dir)
        self.version = os.getenv("CONFIG_VERSION", "1.0.0")
        self.auto_reload = os.getenv("AUTO_RELOAD_CONFIG", "true").lower() == "true"

        # Cache for loaded configs
        self._configs: Dict[str, Any] = {}
        self._file_hashes: Dict[str, str] = {}
        self._last_loaded: Dict[str, datetime] = {}

        logger.info(f"✅ Config loader initialized (version={self.version}, auto_reload={self.auto_reload})")

    def load_job_categories(self, force_reload: bool = False) -> Dict[str, Any]:
        """
        Load job categories configuration

        Args:
            force_reload: Force reload from disk

        Returns:
            Job categories dictionary
        """
        return self._load_config("job_categories.json", force_reload)

    def load_skills_database(self, force_reload: bool = False) -> Dict[str, Any]:
        """
        Load skills database configuration

        Args:
            force_reload: Force reload from disk

        Returns:
            Skills database dictionary
        """
        return self._load_config("skills_database.json", force_reload)

    def load_countries(self, force_reload: bool = False) -> Dict[str, Any]:
        """
        Load countries configuration

        Args:
            force_reload: Force reload from disk

        Returns:
            Countries dictionary
        """
        return self._load_config("countries.json", force_reload)

    def _load_config(self, filename: str, force_reload: bool = False) -> Dict[str, Any]:
        """
        Load configuration file with caching and change detection

        Args:
            filename: Name of config file
            force_reload: Force reload from disk

        Returns:
            Configuration dictionary
        """
        filepath = self.config_dir / filename

        if not filepath.exists():
            logger.error(f"❌ Config file not found: {filepath}")
            return {}

        # Calculate file hash for change detection
        current_hash = self._calculate_file_hash(filepath)

        # Check if we need to reload
        should_reload = (
            force_reload
            or filename not in self._configs
            or (self.auto_reload and current_hash != self._file_hashes.get(filename))
        )

        if should_reload:
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    config_data = json.load(f)

                self._configs[filename] = config_data
                self._file_hashes[filename] = current_hash
                self._last_loaded[filename] = datetime.utcnow()

                logger.info(f"📄 Loaded config: {filename} (hash: {current_hash[:8]}...)")

                # Check if config changed
                if filename in self._file_hashes and current_hash != self._file_hashes.get(filename):
                    logger.warning(f"⚠️ Config changed: {filename}")

            except json.JSONDecodeError as e:
                logger.error(f"❌ Invalid JSON in {filename}: {e}")
                return self._configs.get(filename, {})
            except Exception as e:
                logger.error(f"❌ Error loading {filename}: {e}")
                return self._configs.get(filename, {})

        return self._configs.get(filename, {})

    def _calculate_file_hash(self, filepath: Path) -> str:
        """
        Calculate MD5 hash of file for change detection

        Args:
            filepath: Path to file

        Returns:
            MD5 hash string
        """
        hash_md5 = hashlib.md5()
        with open(filepath, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_md5.update(chunk)
        return hash_md5.hexdigest()

    def reload_all(self):
        """Reload all configuration files"""
        logger.info("🔄 Reloading all configuration files...")

        self.load_job_categories(force_reload=True)
        self.load_skills_database(force_reload=True)
        self.load_countries(force_reload=True)

        logger.info("✅ All configurations reloaded")

    def get_config_info(self) -> Dict[str, Any]:
        """
        Get information about loaded configurations

        Returns:
            Dictionary with config metadata
        """
        return {
            "version": self.version,
            "auto_reload": self.auto_reload,
            "loaded_configs": list(self._configs.keys()),
            "last_loaded_times": {
                filename: timestamp.isoformat()
                for filename, timestamp in self._last_loaded.items()
            },
            "file_hashes": {
                filename: hash_val[:8] + "..."
                for filename, hash_val in self._file_hashes.items()
            }
        }

    def save_config(self, filename: str, data: Dict[str, Any], create_backup: bool = True):
        """
        Save configuration to file

        Args:
            filename: Name of config file
            data: Configuration data to save
            create_backup: Whether to create a backup of existing file
        """
        filepath = self.config_dir / filename

        # Create backup if requested and file exists
        if create_backup and filepath.exists():
            backup_path = filepath.with_suffix(f".backup.{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.json")
            import shutil
            shutil.copy2(filepath, backup_path)
            logger.info(f"💾 Created backup: {backup_path.name}")

        try:
            # Save with pretty printing
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)

            logger.info(f"✅ Saved config: {filename}")

            # Update cache
            self._configs[filename] = data
            self._file_hashes[filename] = self._calculate_file_hash(filepath)
            self._last_loaded[filename] = datetime.utcnow()

        except Exception as e:
            logger.error(f"❌ Error saving {filename}: {e}")
            raise

    def validate_config_version(self, required_version: str) -> bool:
        """
        Validate that current config version meets requirement

        Args:
            required_version: Required minimum version

        Returns:
            True if version is compatible
        """
        def version_tuple(v):
            return tuple(map(int, (v.split("."))))

        current = version_tuple(self.version)
        required = version_tuple(required_version)

        is_compatible = current >= required

        if not is_compatible:
            logger.warning(
                f"⚠️ Config version mismatch: current={self.version}, "
                f"required>={required_version}"
            )

        return is_compatible

    def export_config(self, output_dir: str = "config/exports"):
        """
        Export all configurations to a directory with timestamp

        Args:
            output_dir: Directory to export to
        """
        output_path = Path(output_dir)
        timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
        export_dir = output_path / f"config_export_{timestamp}"
        export_dir.mkdir(parents=True, exist_ok=True)

        # Export each config file
        for filename in self._configs.keys():
            source = self.config_dir / filename
            if source.exists():
                import shutil
                shutil.copy2(source, export_dir / filename)

        # Create metadata file
        metadata = {
            "export_timestamp": datetime.utcnow().isoformat(),
            "config_version": self.version,
            "files": list(self._configs.keys()),
            "file_hashes": self._file_hashes
        }

        with open(export_dir / "metadata.json", 'w') as f:
            json.dump(metadata, f, indent=2)

        logger.info(f"📦 Exported configs to: {export_dir}")
        return export_dir


# Global config loader instance
_config_loader: Optional[ConfigLoader] = None


def get_config_loader() -> ConfigLoader:
    """Get or create global config loader instance"""
    global _config_loader
    if _config_loader is None:
        _config_loader = ConfigLoader()
    return _config_loader


def load_config(config_name: str = "job_categories", force_reload: bool = False) -> Dict[str, Any]:
    """
    Convenience function to load configuration

    Args:
        config_name: Name of config (job_categories, skills_database, countries)
        force_reload: Force reload from disk

    Returns:
        Configuration dictionary
    """
    loader = get_config_loader()

    if config_name == "job_categories":
        return loader.load_job_categories(force_reload)
    elif config_name == "skills_database":
        return loader.load_skills_database(force_reload)
    elif config_name == "countries":
        return loader.load_countries(force_reload)
    else:
        logger.error(f"❌ Unknown config name: {config_name}")
        return {}


if __name__ == "__main__":
    # Test config loader
    loader = ConfigLoader()

    # Load configs
    categories = loader.load_job_categories()
    print(f"Loaded categories: {list(categories.keys())}")

    skills = loader.load_skills_database()
    print(f"Loaded skills: {len(skills)} categories")

    countries = loader.load_countries()
    print(f"Loaded countries: {len(countries.get('countries', []))} countries")

    # Get config info
    info = loader.get_config_info()
    print(f"\nConfig info: {json.dumps(info, indent=2)}")

    # Export configs
    export_dir = loader.export_config()
    print(f"\nExported to: {export_dir}")
