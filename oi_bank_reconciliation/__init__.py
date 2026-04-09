from . import models
from . import wizard

def post_init_hook(env):
    env.ref("account.group_account_manager").write({
        "implied_ids": [(4, env.ref("account.group_account_user").id)]
    })