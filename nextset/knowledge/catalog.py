"""Reviewed method catalogue; no Telegram dependency or workout templates."""
import json
from nextset.platform.paths import RESOURCE_DIR

def references():
    return json.loads((RESOURCE_DIR/'knowledge'/'programs.json').read_text(encoding='utf-8'))

def model_reference(key):
    card=references()[key]
    return {field:card[field] for field in ('title','url','description')}
