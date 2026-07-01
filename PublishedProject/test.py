from concurrent.futures import ProcessPoolExecutor
import time 
import json

with open(f'mosquitofire/saddletimber/errors.txt', "w") as f:
    json.dump([0,0,0], f)