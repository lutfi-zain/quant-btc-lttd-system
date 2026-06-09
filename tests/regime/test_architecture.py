import ast
import os


def test_no_forbidden_imports():
    """
    Assert that the Regime Detection layer (Layer 1) has zero dependency
    on Layer 2 Technical Indicators (src.signals) and Layer 3 Feature Processing (src.features).
    """
    regime_dir = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "../../src/regime")
    )

    assert os.path.exists(regime_dir), f"Directory {regime_dir} does not exist"

    for root, dirs, files in os.walk(regime_dir):
        for file in files:
            if file.endswith(".py"):
                file_path = os.path.join(root, file)
                with open(file_path, "r", encoding="utf-8") as f:
                    content = f.read()

                tree = ast.parse(content, filename=file_path)
                for node in ast.walk(tree):
                    # Check 'import xxx'
                    if isinstance(node, ast.Import):
                        for name in node.names:
                            import_name = name.name
                            # Violation if importing signals/features directly or from src
                            if (
                                import_name == "signals"
                                or import_name.startswith("signals.")
                                or import_name == "features"
                                or import_name.startswith("features.")
                                or import_name == "src.signals"
                                or import_name.startswith("src.signals.")
                                or import_name == "src.features"
                                or import_name.startswith("src.features.")
                            ):
                                raise AssertionError(
                                    f"Architecture Boundary Violation: forbidden import '{import_name}' "
                                    f"found in {os.path.relpath(file_path, regime_dir)}"
                                )

                    # Check 'from xxx import yyy'
                    elif isinstance(node, ast.ImportFrom):
                        module = node.module
                        level = node.level

                        if level == 0 and module:
                            # Absolute import
                            if (
                                module == "signals"
                                or module.startswith("signals.")
                                or module == "features"
                                or module.startswith("features.")
                                or module == "src.signals"
                                or module.startswith("src.signals.")
                                or module == "src.features"
                                or module.startswith("src.features.")
                            ):
                                raise AssertionError(
                                    f"Architecture Boundary Violation: forbidden import 'from {module}' "
                                    f"found in {os.path.relpath(file_path, regime_dir)}"
                                )
                        elif level > 0:
                            # Relative import. Inside src/regime/, level=1 is src/regime, level=2 is src/
                            # e.g., from ..signals import base -> level=2, module=signals
                            # e.g., from .features import prepare_features -> level=1, module=features
                            if level >= 2 and module:
                                if (
                                    module == "signals"
                                    or module.startswith("signals.")
                                    or module == "features"
                                    or module.startswith("features.")
                                ):
                                    raise AssertionError(
                                        f"Architecture Boundary Violation: forbidden relative import 'from {'.' * level}{module}' "
                                        f"found in {os.path.relpath(file_path, regime_dir)}"
                                    )
