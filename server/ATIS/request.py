import requests
import json
from tabulate import tabulate

atisdata = None

def get_airwaysn_data():
    url = "https://data.airwaysn.org/v1/data.json"
    try:
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
        return data
    except requests.exceptions.RequestException as e:
        print(f"Error fetching data: {e}")
    except json.JSONDecodeError as e:
        print(f"Error parsing JSON: {e}")
    return None

def display_atis_table(data):
    if not data or 'atis' not in data:
        print("No ATIS data available")
        return None
    
    # 准备表格数据
    table_data = []
    for atis in data['atis']:
        callsign = atis.get('callsign', 'N/A')
        frequency = atis.get('frequency', 'N/A')
        text = '\n'.join(atis.get('text_atis', ['N/A']))
        table_data.append([callsign, frequency, text])
    
    # 创建并显示表格
    print(table_data)
    return table_data

if __name__ == "__main__":
    data = get_airwaysn_data()
    if data:
        display_atis_table(data)