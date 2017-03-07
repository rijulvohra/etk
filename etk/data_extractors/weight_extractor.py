import re

######################################################################
#   Constant
######################################################################

# Constants for weight
WEIGHT_UNIT_POUND = 'pound'
WEIGHT_UNIT_KILOGRAM = 'kilogram'

WEIGHT_UNIT_POUND_ABBRS = ['lb', 'lbs']
WEIGHT_UNIT_KILOGRAM_ABBRS = ['kg']

WEIGHT_UNITS_DICT = {
    WEIGHT_UNIT_POUND: WEIGHT_UNIT_POUND_ABBRS,
    WEIGHT_UNIT_KILOGRAM: WEIGHT_UNIT_KILOGRAM_ABBRS
}

# Transform
WEIGHT_TRANSFORM_DICT = {
    (WEIGHT_UNIT_POUND, WEIGHT_UNIT_POUND): 1,
    (WEIGHT_UNIT_POUND, WEIGHT_UNIT_KILOGRAM): 0.45359237,
    (WEIGHT_UNIT_KILOGRAM, WEIGHT_UNIT_POUND): 2.2046,
    (WEIGHT_UNIT_KILOGRAM, WEIGHT_UNIT_KILOGRAM): 1,
}


######################################################################
#   Regular Expression
######################################################################

reg_us_weight_unit_lb = r'\b\d{2,3}[ ]*(?:lb|lbs)\b'
reg_us_weight_unit_kg = r'\b\d{2}[ ]*kg\b'

re_us_weight = re.compile(r'(?:' + r'|'.join([
    reg_us_weight_unit_lb,
    reg_us_weight_unit_kg
]) + r')', re.IGNORECASE)

reg_ls_weight = r'(?<=weight)[: \n]*' + r'(?:' + r'|'.join([
    reg_us_weight_unit_lb,
    reg_us_weight_unit_kg,
    r'(?:\d{1,3})'
]) + r')'

re_ls_weight = re.compile(reg_ls_weight, re.IGNORECASE)

######################################################################
#   Main Class
######################################################################




def clean_extraction(extraction):
    extraction = extraction.replace(':', '')
    extraction = extraction.lower().strip()
    return extraction


def remove_dups(extractions):
    return [dict(_) for _ in set([tuple(dict_item.items()) for dict_item in extractions if dict_item])]

######################################################################
#   Normalize
######################################################################

def normalize_weight(extraction):
    extraction = clean_extraction(extraction)
    ans = {}
    if 'lb' in extraction:
        value, remaining = extraction.split('lb')
        ans[WEIGHT_UNIT_POUND] = int(value.strip())
    elif 'kg' in extraction:
        value, remaining = extraction.split('kg')
        ans[WEIGHT_UNIT_KILOGRAM] = int(value.strip())
    elif extraction.isdigit():
        if len(extraction) == 2:
            ans[WEIGHT_UNIT_KILOGRAM] = int(extraction)
        elif len(extraction) == 3:
            ans[WEIGHT_UNIT_POUND] = int(extraction)
        else:
            print 'WARNING: contain uncatched case:', extraction

    return ans

######################################################################
#   Unit Transform
######################################################################

def transform(extractions, target_unit):
    ans = []
    for extraction in extractions:
        imd_value = 0.
        for (unit, value) in extraction.iteritems():
            imd_value += WEIGHT_TRANSFORM_DICT[(unit, target_unit)] * value
        if sanity_check(target_unit, imd_value):
            ans.append(imd_value)
    return ans

######################################################################
#   Sanity Check
######################################################################

def sanity_check(unit, value):
    if (unit, WEIGHT_UNIT_KILOGRAM) in WEIGHT_TRANSFORM_DICT:
        check_value = WEIGHT_TRANSFORM_DICT[
            (unit, WEIGHT_UNIT_KILOGRAM)] * value
        if check_value >= 30 and check_value <= 200:    # kg
            return True
    return False

######################################################################
#   Output Format
######################################################################

def format_output(value):
    return int(value)


######################################################################
#   Main
######################################################################



def weight_extract(text):
    
    weight_extractions = re_us_weight.findall(text) + re_ls_weight.findall(text)

    weight_extractions = remove_dups(
        [normalize_weight(_) for _ in weight_extractions])

    weight = {'raw': weight_extractions}

    for target_unit in [WEIGHT_UNIT_KILOGRAM, WEIGHT_UNIT_POUND]:
        weight[target_unit] = [format_output(_) for _ in
                               transform(weight_extractions, target_unit)]
    output = {}

    if len(weight['raw']) > 0:
        output['weight'] = weight

    if 'weight' not in output:
        return None

    return output