from pathlib import Path
import yaml
from pydantic import BaseModel
from typing import List


class Framework(BaseModel):
    name: str
    controls: dict


def load_frameworks(names: List[str]) -> List[Framework]:
    framework_dir = Path(__file__).parent.parent / "frameworks"
    frameworks = []
    for name in names:
        file = framework_dir / f"{name}.yaml"
        if file.exists():
            with open(file, "r") as f:
                data = yaml.safe_load(f)
            frameworks.append(Framework(name=name, controls=data))
    return frameworks
