import argparse
import redis
from urllib.parse import urlparse

MIN_REDIS_GEARS_VER = 'v1.0.0'
MIN_REDIS_AI_VER = 'v1.0.2'

def semver_to_integer(v):
    v = v.strip('v').split('.')
    v = ['0' + ver if len(ver) == 1 else ver for ver in v ]
    ver = int("".join(v))

    return ver

def integer_to_semver(v):
    ver = ""
    for _ in range(3):
        if ver != "":
            ver = "." + ver
        ver = str(v % 100) + ver
        v = v // 100

    return "v" + ver


if __name__ == '__main__':
    # Parse arguments
    parser = argparse.ArgumentParser()
    parser.add_argument('-u', '--url', help='Redis URL', type=str, default='redis://127.0.0.1:6379')
    args = parser.parse_args()

    # Set up some vars
    initialized_key = 'cats:initialized'

    # Set up Redis connection
    url = urlparse(args.url)
    conn = redis.Redis(host=url.hostname, port=url.port)
    if not conn.ping():
        raise Exception('Redis unavailable')

    # check RedisGears and RedisAI versions
    modules = conn.execute_command('MODULE', 'LIST')
    for module in modules:
        # RedisGears
        if module[1].decode('ascii') == 'rg':
            if int(module[3]) < semver_to_integer(MIN_REDIS_GEARS_VER):
                print("Running Redis Gears version is {}. Version >= {} required.".format(integer_to_semver(module[3]), MIN_REDIS_GEARS_VER))
                exit(0)
        # redisAI
        elif module[1].decode('ascii') == 'ai':
            if int(module[3]) < semver_to_integer(MIN_REDIS_AI_VER):
                print("Running Redis Gears version is {}. Version >= {} required.".format(integer_to_semver(module[3]), MIN_REDIS_AI_VER))
                exit(0)

    # Check if this Redis instance had already been initialized
    initialized = conn.exists(initialized_key)
    if initialized:
        print('Discovered evidence of a previous initialization - skipping.')
        exit(0)

    # Load the RedisAI model
    print('Loading model - ', end='')
    with open('models/mobilenet_v2_1.4_224_frozen.pb', 'rb') as f:
        model = f.read()
        res = conn.execute_command('AI.MODELSET', 'mobilenet:model', 'TF', 'CPU', 'INPUTS', 'input', 'OUTPUTS', 'MobilenetV2/Predictions/Reshape_1', 'BLOB', model)
        print(res)

    # Load the gear
    print('Loading gear - ', end='')
    with open('gear.py', 'rb') as f:
        gear = f.read()
        # Add required dependencies to the parameter if required. For instance:
        #   res = conn.execute_command('RG.PYEXECUTE', gear, 'REQUIREMENTS', 'opencv-python', 'imageio')
        res = conn.execute_command('RG.PYEXECUTE', gear)
        print(res)

    # Lastly, set a key that indicates initialization has been performed
    print('Flag initialization as done - ', end='')
    print(conn.set(initialized_key, 'miauw'))
