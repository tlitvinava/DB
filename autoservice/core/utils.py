def is_client(user):
    return user.role and user.role.rolename == "CLIENT"

def is_master(user):
    return user.role and user.role.rolename == "MASTER"

def is_admin(user):
    return user.role and user.role.rolename == "ADMIN"
