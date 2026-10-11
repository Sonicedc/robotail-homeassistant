"""Load the standalone client without Home Assistant's runtime entry point."""

import sys
import types
from pathlib import Path

package = types.ModuleType("custom_components.robotail")
package.__path__ = [
    str(Path(__file__).resolve().parents[1] / "custom_components" / "robotail")
]
sys.modules["custom_components.robotail"] = package
