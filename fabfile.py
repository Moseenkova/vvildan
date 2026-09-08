from fabric import task

my_hosts = ["bikmetle@151.245.139.36:22"]


@task(hosts=my_hosts)
def deploy_front(c, branch="frontend"):
    """
    for other branches: fab deploy_front --branch=BRANCH_NAME
    """
    app_path = "/home/bikmetle/vvildan"
    commands = [
        f"git fetch origin && git reset --hard origin/{branch}",
        "source .venv/bin/activate && alembic upgrade head",
        "docker-compose down",
        "docker-compose up -d --build",
        "docker image prune -f",
        "docker builder prune -f",
    ]

    for command in commands:
        c.run(f"cd {app_path} && {command}")
