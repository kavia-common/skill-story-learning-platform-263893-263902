import json
import os

from src.api.main import app

# Generate and write the OpenAPI schema for external consumption
# PUBLIC_INTERFACE
def generate_and_write_openapi():
    """Generate and write OpenAPI schema to interfaces/openapi.json."""
    openapi_schema = app.openapi()
    output_dir = "interfaces"
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, "openapi.json")
    with open(output_path, "w") as f:
        json.dump(openapi_schema, f, indent=2)
    return output_path


if __name__ == "__main__":
    generate_and_write_openapi()
