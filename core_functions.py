import importlib.util
import hashlib
import json
from typing import Dict
from pathlib import Path
from functools import lru_cache
from tools.video_to_text import process_new_videos
from dotenv import load_dotenv
import logging
import hashlib


load_dotenv()
logger = logging.getLogger(__name__)


class IntegrationLoader:
    def __init__(self, integrations_dir: str = "integrations"):
        self.integrations_dir = Path(integrations_dir)

    def import_integrations(self) -> Dict[str, object]:
        """
        Import all valid integration modules from the integrations directory.
        Returns a dictionary of module names and their corresponding modules.
        """
        if not self.integrations_dir.exists():
            print(f"Integration directory '{self.integrations_dir}' not found")
            return {}

        modules = {}
        for file_path in self.integrations_dir.glob("*.py"):
            if file_path.name.startswith("__"):
                continue

            try:
                module_name = file_path.stem
                spec = importlib.util.spec_from_file_location(
                    module_name, str(file_path)
                )
                if spec and spec.loader:
                    module = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(module)
                    if hasattr(module, "run"):
                        modules[module_name] = module
                        print(f"Successfully loaded integration: {module_name}")
                    else:
                        print(f"Skipped {module_name}: missing 'run' function")
            except Exception as e:
                print(f"Error loading {file_path.name}: {e}")
                continue

        return modules

    def list_available_integrations(self) -> list:
        """List all available integration files in the directory."""
        if not self.integrations_dir.exists():
            return []

        return [
            f.stem
            for f in self.integrations_dir.glob("*.py")
            if not f.name.startswith("__")
        ]

    def run_integration(self, module_name: str) -> bool:
        """
        Run a specific integration by module name.
        Returns True if successful, False otherwise.
        """
        modules = self.import_integrations()
        if module_name not in modules:
            print(f"Integration '{module_name}' not found")
            return False

        try:
            modules[module_name].run()
            return True
        except Exception as e:
            print(f"Error running {module_name}: {e}")
            return False


class KnowledgeManager:
    def __init__(self, base_dir: str = "."):
        self.base_dir = Path(base_dir)
        self.knowledge_path = self.base_dir / "knowledge_base"
        self.hash_file = self.knowledge_path / ".hash"
        self.instructions_file = self.base_dir / "instructions.txt"
        self.videos_path = self.base_dir / "videos"
        self.videos_hash_file = self.videos_path / ".hash"

        logging.basicConfig(level=logging.DEBUG)
        self.logger = logging.getLogger(__name__)

    @lru_cache(maxsize=1)
    def load_instructions(self) -> str:
        """Loads and caches instructions."""

        try:
            instructions = self.instructions_file.read_text(encoding="utf-8").strip()
            print(
                f"Loaded instructions: {instructions[:100]}"
            )  # Print the first 100 chars for quick verification
            return instructions
        except FileNotFoundError:
            print("Instructions file not found")
            return "Respond concisely and to the point."

    def get_file_hash(self, file_path: Path) -> str:
        """Calculate file hash using SHA256."""
        hasher = hashlib.sha256()
        with file_path.open("rb") as f:
            while chunk := f.read(8192):
                hasher.update(chunk)
        return hasher.hexdigest()

    def get_folder_hash(self, folder_path: Path) -> str:
        """Calculate a stable hash for a folder, including the contents of all files."""
        if not folder_path.exists() or not folder_path.is_dir():
            return ""

        hasher = hashlib.md5()

        files = sorted(
            (
                p
                for p in folder_path.rglob("*")
                if p.is_file() and not p.name.startswith(".")
            ),
            key=lambda x: x.relative_to(folder_path).as_posix(),
        )

        for file_path in files:
            try:
                rel_path = file_path.relative_to(folder_path).as_posix().encode("utf-8")
                hasher.update(rel_path)

                content = file_path.read_bytes()  # Читаем файл в бинарном режиме
                hasher.update(content)
            except Exception as e:
                print(f"Ошибка чтения {file_path}: {e}")

        return hasher.hexdigest()

    def load_knowledge_base(self) -> str:
        """Load knowledge base with efficient file handling."""
        if not self.knowledge_path.exists():
            self.logger.warning("Knowledge base directory does not exist.")
            print("Knowledge base directory does not exist.")
            return "No data in the knowledge base."

        knowledge_parts = []
        for file_path in sorted(self.knowledge_path.glob("*")):
            if file_path.suffix == ".txt":
                knowledge_parts.append(
                    f"\n=== {file_path.name} ===\n{file_path.read_text(encoding='utf-8')}"
                )
            elif file_path.suffix == ".json":
                try:
                    data = json.loads(file_path.read_text(encoding="utf-8"))
                    knowledge_parts.append(
                        f"\n=== {file_path.name} ===\n{json.dumps(data, indent=4)}"
                    )
                except json.JSONDecodeError:
                    self.logger.warning(f"Failed to parse JSON file: {file_path.name}")
                    continue

        # Log the knowledge content before saving
        if knowledge_parts:
            knowledge_text = "\n".join(knowledge_parts)
            self.logger.debug(f"Knowledge base content:\n{knowledge_text[:500]}...")
            knowledge_file_path = self.base_dir / "ai_assistant/knowledge_base.txt"
            try:
                with open(knowledge_file_path, "r", encoding="utf-8") as f:
                    content = f.read()
                    if len(content) < 10:
                        logger.error("Knowledge base file is empty or too small")
                        return None
                    logger.info(
                        f"Knowledge base loaded successfully with {len(content)} characters"
                    )
                    return str(knowledge_file_path)
            except Exception as e:
                logger.error(f"Failed to verify knowledge base file: {e}")
                return None

        self.logger.warning("No data found in the knowledge base.")
        return "No data in the knowledge base."

    def check_and_update_knowledge(self) -> bool:
        """Check for knowledge base updates efficiently."""
        new_hash = self.get_folder_hash(self.knowledge_path)
        try:
            old_hash = self.hash_file.read_text().strip()
            print(f"[DEBUG] Old hash: {old_hash}")
        except FileNotFoundError:
            old_hash = ""

        print(f"[DEBUG] New hash: {new_hash}")

        if new_hash != old_hash:
            self.load_knowledge_base()
            self.hash_file.write_text(new_hash)
            return True
        return False


class VideoManager:
    def __init__(self, videos_path: str, hash_file: str):
        self.video_ids_path = Path(videos_path) / "video_ids.json"
        self.videos_hash_file = Path(hash_file)

    def get_file_hash(self, file_path: Path) -> str:
        """Returns the hash of the file content."""
        if not file_path.exists():
            return ""

        hasher = hashlib.md5()
        with file_path.open("rb") as f:
            hasher.update(f.read())
        return hasher.hexdigest()

    def check_and_update_videos(self) -> bool:
        """Checks for changes in video_ids.json and triggers processing if needed."""
        new_hash = self.get_file_hash(self.video_ids_path)

        try:
            old_hash = self.videos_hash_file.read_text().strip()
        except FileNotFoundError:
            old_hash = ""

        if new_hash != old_hash:
            self.videos_hash_file.write_text(new_hash)
            self.process_new_videos()
            return True
        return False

    def process_new_videos(self):
        """Triggers the video processing script."""
        try:
            process_new_videos()
        except ImportError as e:
            print(f"Error importing video processing module: {e}")


class SystemManager:
    def __init__(self):
        self.knowledge_manager = KnowledgeManager()
        self.video_manager = VideoManager("videos", "video_hash.txt")
        self.integration_loader = IntegrationLoader()

    def run_system(self):
        """Check updates in knowledge base and videos, then run integrations."""
        videos_updated = self.video_manager.check_and_update_videos()

        if videos_updated:
            print("Updates detected. Running integrations...")
            self.run_integrations()
        else:
            print("No updates detected. Running integrations.")
            self.run_integrations()

    def run_integrations(self):
        """Load and execute all available integrations."""
        modules = self.integration_loader.import_integrations()
        for module_name, module in modules.items():
            try:
                print(f"Running integration: {module_name}")
                module.run()
            except Exception as e:
                print(f"Error running {module_name}: {e}")
