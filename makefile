# Config
MODELS_DIR := public_invest_api/models

# Targets
.PHONY: all setup generate clean

all: generate

# Create necessary folders and unzip the .proto archive
setup:
	@echo "Setting up directories..."
	mkdir -p $(MODELS_DIR)

# Generate Python stubs
generate: setup
	@echo "Generating Pydantic files..."
	uv run datamodel-codegen \
		--input public_invest_openapi_spec/Public\ API\ Spec\ Doc.json \
		--input-file-type openapi \
		--output public_invest_api/models/ --output-model-type pydantic_v2.BaseModel
	@echo "Generation complete. Files written to $(MODELS_DIR)."

# Clean generated code
clean:
	@echo "Cleaning generated Pydantic files..."
	rm -rf $(MODELS_DIR)
	@echo "Clean complete."
