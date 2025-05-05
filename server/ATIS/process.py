import re

chinese_numbers = {
    0: "洞",
    1: "幺",
    2: "两",
    3: "三",
    4: "四",
    5: "五",
    6: "六",
    7: "拐",
    8: "八",
    9: "九",
}

english_numbers = {
    0: "zero",
    1: "one",
    2: "two",
    3: "three",
    4: "four",
    5: "five",
    6: "six",
    7: "seven",
    8: "eight",
    9: "niner",
}

english_characters = {
    "A": "Alpha",
    "B": "Bravo",
    "C": "Charlie",
    "D": "Delta",
    "E": "Echo",
    "F": "Foxtrot",
    "G": "Golf",
    "H": "Hotel",
    "I": "India",
    "J": "Juliett",
    "K": "Kilo",
    "L": "Lima",
    "M": "Mike",
    "N": "November",
    "O": "Oscar",
    "P": "Papa",
    "Q": "Quebec",
    "R": "Romeo",
    "S": "Sierra",
    "T": "Tango",
    "U": "Uniform",
    "V": "Victor",
    "W": "Whiskey",
    "X": "X-ray",
    "Y": "Yankee",
    "Z": "Zulu"
}

def process_mixed_atis_text(text):
    """
    处理ATIS文本，可以处理纯英文或中英文混合的情况
    如果文本包含|符号，则认为是中英文混合，英文在前中文在后
    """
    if not text:
        return text
    
    # 检查是否有中英文分隔符
    parts = text.split('|')
    
    if len(parts) == 2:
        # 有中英文分隔的情况
        english_part = process_single_atis_text(parts[0].strip(), is_chinese=False)
        chinese_part = process_single_atis_text(parts[1].strip(), is_chinese=True)
        return f"{english_part}|{chinese_part}"
    else:
        # 纯英文的情况
        return process_single_atis_text(text, is_chinese=False)

def process_single_atis_text(text, is_chinese=False):
    """
    处理单一语言的ATIS文本，替换字母和数字为对应的无线电读法
    is_chinese: 是否为中文ATIS
    """
    # print (f"处理ATIS文本: {text}, 中文: {is_chinese}")
    # 给待处理的文本最后加上一个空格
    text = text.strip() + " "
    
    if not text:
        return text
        
    # 选择对应的数字读法字典
    number_dict = chinese_numbers if is_chinese else english_numbers
    
    # 处理空格+大写字母+空格的模式
    def replace_letter(match):
        letter = match.group(1)
        return f" {english_characters.get(letter, letter)} "
    
    text = re.sub(r'\s([A-Z])\s', replace_letter, text)
    
    # 处理数字
    def replace_number(match):
        number = match.group(0)
        number_text = " ".join(number_dict[int(digit)] for digit in number)
        return f" {number_text} "
    
    text = re.sub(r'\d+', replace_number, text)
    return text

