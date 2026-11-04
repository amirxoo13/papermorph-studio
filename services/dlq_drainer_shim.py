import importlib.util
from pathlib import Path
spec = importlib.util.spec_from_file_location('dlq_main', Path(__file__).parent / 'dlq-drainer' / 'src' / 'main.py')
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
process_dlq_message = mod.process_dlq_message
