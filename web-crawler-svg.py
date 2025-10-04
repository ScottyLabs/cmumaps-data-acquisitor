import requests

cookies1 = {
}

headers1 = {
}

floor = dict()

floor[1] = 'B17B8318AE'
floor[2] = 'B3694BB100'
floor["a"] = 'A9D1E1D19B'
floor["b"] = '983D8F70C0'
floor["c"] = 'ED527CF2D4'
floor["d"] = '745AEBB740'

params = {
    'floorId': 'B17B8318AE',
    'isRevit': 'false',
    'RoomBoundaryLayer': 'A-AREA',
    'RoomTagLayer': 'A-AREA-IDEN',
    'svgFile': 'ansys-1-esim.svg',
    # '_': '1751603944158',
}

for floor_num, floor_id in floor.items():
    params['floorId'] = floor_id
    params['svgFile'] = f'ansys-{floor_num}-esim.svg'

    response = requests.get(
        'https://fmsystems.cmu.edu/FMInteract/tools/getDefaultLayersData.ashx',
        params=params,
        cookies=cookies1,
        headers=headers1,
        verify=False,
    )

    with open(f"svg_files/Ansys-{floor_num}-map.svg", "w") as f:
        f.write(response.text)

params['floorId'] = '745AEBB740'
params['svgFile'] = 'ansys-d-fesim.svg'

response = requests.get(
    'https://fmsystems.cmu.edu/FMInteract/tools/getDefaultLayersData.ashx',
    params=params,
    cookies=cookies1,
    headers=headers1,
    verify=False,
)

with open(f"svg_files/Ansys-d-map.svg", "w") as f:
    f.write(response.text)