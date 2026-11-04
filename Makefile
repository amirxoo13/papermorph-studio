PROJECT_ID ?= gen-lang-client-0484425781
REGION ?= us-central1

.PHONY: init validate plan apply test smoke destroy

init:
	cd infra && terraform init -backend=false

validate:
	cd infra && terraform validate

test:
	pytest services/agents/tests services/mcp-tools/tests services/render-job/tests services/api/tests

smoke:
	bash scripts/smoke_test.sh

destroy:
	cd infra && terraform destroy -var-file=env/dev.tfvars -auto-approve
