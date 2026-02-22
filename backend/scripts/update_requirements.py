import os
import sys

# Use Python’s built-in metadata API (no pkg_resources)
try:
    from importlib.metadata import PackageNotFoundError, version
except ImportError:
    from importlib_metadata import PackageNotFoundError, version


def update_requirements(file_path="requirements.txt"):
    if not os.path.exists(file_path):
        print(f"❌ File not found: {file_path}")
        sys.exit(1)

    with open(file_path, "r") as f:
        lines = f.readlines()

    updated_lines = []
    for line in lines:
        stripped = line.strip()

        # Preserve comments and blank lines
        if not stripped or stripped.startswith("#"):
            updated_lines.append(line)
            continue

        # Extract package (full), base package (without extras)
        pkg_full = stripped.split("==")[0].strip()
        pkg = pkg_full.split("[")[0]  # Remove extras

        try:
            pkg_version = version(pkg)
            updated_lines.append(f"{pkg_full}=={pkg_version}\n")
        except PackageNotFoundError:
            print(f"⚠️  Package '{pkg_full}' not installed — leaving as is.")
            updated_lines.append(line if line.endswith("\n") else line + "\n")

    with open(file_path, "w") as f:
        f.writelines(updated_lines)

    print(f"✅ Updated {file_path} with installed package versions!")


if __name__ == "__main__":
    update_requirements()
