from . import controllers
from . import models


def post_init_hook(env_or_cr, registry=None):
    """Load notification rows for every installed app. All stay off."""
    if registry is not None:
        from odoo import SUPERUSER_ID, api
        env = api.Environment(env_or_cr, SUPERUSER_ID, {})
    else:
        env = env_or_cr
    env["wanoti.rule"]._refresh_events()
