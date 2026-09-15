from paddleocr import PaddleOCR as pcr

import re


# spatial functions start

# ________________________________________________________________________________________________

def get_center(box):

    x1, y1, x2, y2 = box

    center_x = (x1 + x2) / 2
    center_y = (y1 + y2) / 2

    return center_x, center_y


def distance(box1, box2):

    x1, y1 = get_center(box1)
    x2, y2 = get_center(box2)

    return ((x2 - x1) ** 2 + (y2 - y1) ** 2) ** 0.5


def is_same_line(box1, box2, tolerance=25):

    _, y1 = get_center(box1)
    _, y2 = get_center(box2)

    return abs(y1 - y2) <= tolerance


def is_to_right(box1, box2):

    x1, _, x2, _ = box1
    x1_other, _, _, _ = box2

    return x2 < x1_other


def is_below(box1, box2):

    _, y1 = get_center(box1)
    _, y2 = get_center(box2)

    return y2 > y1


def is_horizontally_overlapping(box1, box2):

    left1, _, right1, _ = box1
    left2, _, right2, _ = box2

    return left1 < right2 and right1 > left2


# spatial end lol

# ________________________________________________________________________________________________


# label & value finder

# ________________________________________________________________________________________________


# MRP

def get_mrp(text):

    # first check if the text actually contains an mrp label

    if re.search(
        r"m\.?\s*r\.?\s*p\.?|max\.?\s*retail\s*price",
        text,
        re.I
    ):

        # checking the ₹/Rs case first

        result = re.search(
            r"(?:₹|Rs\.?)\s*[:.]?\s*(\d+(?:\.\d{1,2})?)",
            text,
            re.I
        )

        # in case ocr couldn't find the symbols for rate

        if not result:

            result = re.search(
                r"(\d+(?:\.\d{1,2})?)",
                text
            )

        if result:

            # return only the value without symbol and label name

            return result.group(1)

    return None


# quantity

def get_quantity(text):

    result = re.search(
        r"\d+(?:\.\d+)?\s*(?:kg|g|ml|l|unit|u|n)\b",
        text,
        re.I
    )

    if result:

        return result.group()

    return None


# date

def get_date(text):

    # checking for month-year formats first
    # examples - july-2025, july 2025, july/2025

    result = re.search(
        r"(?:"
        r"jan(?:uary)?|"
        r"feb(?:ruary)?|"
        r"mar(?:ch)?|"
        r"apr(?:il)?|"
        r"may|"
        r"jun(?:e)?|"
        r"jul(?:y)?|"
        r"aug(?:ust)?|"
        r"sep(?:t(?:ember)?)?|"
        r"oct(?:ober)?|"
        r"nov(?:ember)?|"
        r"dec(?:ember)?"
        r")"
        r"[-/\s]?\d{4}",
        text,
        re.I
    )

    if result:

        return result.group()

    # checking for formats like 02/2025 or 09-2025

    result = re.search(
        r"\b\d{1,2}[/-]\d{4}\b",
        text
    )

    if result:

        return result.group()

    # checking for formats like 2025-07

    result = re.search(
        r"\b\d{4}[/-]\d{1,2}\b",
        text
    )

    if result:

        return result.group()

    return None


# email

def get_email(text):

    result = re.search(
        r"\b[A-Za-z0-9._%+-]+@"
        r"[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b",
        text
    )

    if result:

        return result.group()

    return None


# phone number

def get_phone(text):

    result = re.search(
        r"(?:\+91[\s-]?)?[6-9]\d{9}\b",
        text
    )

    if result:

        return result.group()

    return None


# ________________________________________________________________________________________________


# candidate finder

# ________________________________________________________________________________________________


def find_matching_candidate(candidates, pattern):

    # go through the nearby text and find the one
    # that matches the regex we are looking for

    for item in candidates:

        result = re.search(
            pattern,
            item["text"],
            re.I
        )

        if result:

            return item

    return None


def find_candidates(label_box):

    candidates = []

    for item in ocr_data:

        box = item["box"]

        # don't compare the label with itself

        if box == label_box:
            continue

        # value is on the same line and to the right

        if (
            is_same_line(label_box, box)
            and is_to_right(label_box, box)
        ):

            candidates.append(item)

        # value is below the label and overlaps horizontally

        elif (
            is_below(label_box, box)
            and is_horizontally_overlapping(label_box, box)
        ):

            candidates.append(item)

    # closest candidates first

    candidates.sort(
        key=lambda item: distance(
            label_box,
            item["box"]
        )
    )

    return candidates


# ________________________________________________________________________________________________


# field finder

# ________________________________________________________________________________________________


# find mrp

def find_mrp():

    # first check if mrp and its value are in the same ocr box

    for item in ocr_data:

        value = get_mrp(item["text"])

        if value:

            return {
                "value": value,
                "confidence": item["confidence"],
                "source": item["text"]
            }

    # if they are separate, find the mrp label first

    for item in ocr_data:

        if re.search(
            r"m\.?\s*r\.?\s*p\.?|max\.?\s*retail\s*price",
            item["text"],
            re.I
        ):

            candidates = find_candidates(
                item["box"]
            )

            # checking for ₹ or rs first

            result = find_matching_candidate(
                candidates,
                r"(?:₹|Rs\.?)\s*\d+(?:\.\d{1,2})?"
            )

            if result:

                amount = re.search(
                    r"\d+(?:\.\d{1,2})?",
                    result["text"]
                )

                if amount:

                    return {
                        "value": amount.group(),
                        "confidence": result["confidence"],
                        "source": result["text"]
                    }

            # if ocr missed the currency symbol,
            # just look for a number

            result = find_matching_candidate(
                candidates,
                r"\b\d+(?:\.\d{1,2})?\b"
            )

            if result:

                amount = re.search(
                    r"\d+(?:\.\d{1,2})?",
                    result["text"]
                )

                if amount:

                    return {
                        "value": amount.group(),
                        "confidence": result["confidence"],
                        "source": result["text"]
                    }

    return None


# find quantity

def find_quantity():

    # first check if the label and value are in the same box

    for item in ocr_data:

        if re.search(
            r"net\s*(?:qty|quantity)",
            item["text"],
            re.I
        ):

            quantity = get_quantity(
                item["text"]
            )

            if quantity:

                return {
                    "value": quantity,
                    "confidence": item["confidence"],
                    "source": item["text"]
                }

    # if the value is in another box,
    # find the value near the net quantity label

    for item in ocr_data:

        if re.search(
            r"net\s*(?:qty|quantity)",
            item["text"],
            re.I
        ):

            candidates = find_candidates(
                item["box"]
            )

            result = find_matching_candidate(
                candidates,
                r"\d+(?:\.\d+)?\s*(?:kg|g|ml|l|unit|u|n)\b"
            )

            if result:

                quantity = get_quantity(
                    result["text"]
                )

                if quantity:

                    return {
                        "value": quantity,
                        "confidence": result["confidence"],
                        "source": result["text"]
                    }

    return None


# find manufacturing date

def find_manufacturing_date():

    # these are the labels we are looking for

    date_label = (
        r"mfg\.?\s*date"
        r"|"
        r"manufacturing\s*date"
        r"|"
        r"date\s*of\s*manufacture"
        r"|"
        r"month\s*/?\s*year\s*of\s*mfg"
    )

    # first check if label and date are in the same box

    for item in ocr_data:

        if re.search(
            date_label,
            item["text"],
            re.I
        ):

            date = get_date(
                item["text"]
            )

            if date:

                return {
                    "value": date,
                    "confidence": item["confidence"],
                    "source": item["text"]
                }

    # otherwise find the date near the label

    for item in ocr_data:

        if re.search(
            date_label,
            item["text"],
            re.I
        ):

            candidates = find_candidates(
                item["box"]
            )

            for candidate in candidates:

                date = get_date(
                    candidate["text"]
                )

                if date:

                    return {
                        "value": date,
                        "confidence": candidate["confidence"],
                        "source": candidate["text"]
                    }

    return None


# find manufacturer

def find_manufacturer():

    # first check if manufacturer and name are in the same box

    for item in ocr_data:

        text = item["text"]

        result = re.search(
            r"manufactured\s+(?:and\s+marketed\s+)?by"
            r"\s*[:\-]\s*(.+)",
            text,
            re.I
        )

        if result:

            value = result.group(1).strip()

            if value:

                return {
                    "value": value,
                    "confidence": item["confidence"],
                    "source": item["text"]
                }

    # if the name is in another box,
    # find the manufacturer label first

    for item in ocr_data:

        text = item["text"]

        if re.search(
            r"manufactured\s+(?:and\s+marketed\s+)?by"
            r"|manufacturer",
            text,
            re.I
        ):

            candidates = find_candidates(
                item["box"]
            )

            # check the nearby candidates

            for candidate in candidates:

                text = candidate["text"].strip()

                # remove symbols that ocr may have picked up

                text = text.lstrip("*:,- ")

                # skip other labels

                if re.search(
                    r"net\s*(?:qty|quantity)"
                    r"|m\.?\s*r\.?\s*p\.?"
                    r"|max\.?\s*retail\s*price"
                    r"|mfg\.?\s*date"
                    r"|commodity"
                    r"|consumer"
                    r"|inclusive",
                    text,
                    re.I
                ):
                    continue

                # skip empty or very short text

                if not text or len(text) < 3:
                    continue

                # skip things that are only numbers or symbols

                if re.fullmatch(
                    r"[\d\s.,:/\-]+",
                    text
                ):
                    continue

                return {
                    "value": text,
                    "confidence": candidate["confidence"],
                    "source": candidate["text"]
                }

    return None



# find commodity

def find_commodity():

    # first check if commodity and its value are in the same ocr box
    for item in ocr_data:

        result = re.search(
            r"commodity\s*[:\-]?\s*(.+)",
            item["text"],
            re.I
        )

        if result:

            value = result.group(1).strip()

            if value:

                return {
                    "value": value,
                    "confidence": item["confidence"],
                    "source": item["text"]
                }

    # if the value is in another box, find the commodity label first
    for item in ocr_data:

        if re.search(r"\bcommodity\b", item["text"], re.I):

            candidates = find_candidates(item["box"])

            # look through nearby candidates
            for candidate in candidates:

                value = candidate["text"].strip()

                # remove symbols that ocr may have picked up
                value = value.lstrip("*:,- ")

                if not value or len(value) < 2:
                    continue

                # skip other known labels
                if re.search(
                    r"net\s*(?:qty|quantity)"
                    r"|m\.?\s*r\.?\s*p\.?"
                    r"|max\.?\s*retail\s*price"
                    r"|mfg\.?\s*date"
                    r"|manufacturing\s*date"
                    r"|manufacturer"
                    r"|consumer"
                    r"|inclusive"
                    r"|usp",
                    value,
                    re.I
                ):
                    continue

                # skip values that contain only numbers or symbols
                if re.fullmatch(r"[\d\s.,:/\-]+", value):
                    continue

                return {
                    "value": value,
                    "confidence": candidate["confidence"],
                    "source": candidate["text"]
                }

    return None


# find country of origin

def find_country_of_origin():

    # look for things like - made in india

    for item in ocr_data:

        result = re.search(
            r"\bmade\s+in\s+([A-Za-z ]+)",
            item["text"],
            re.I
        )

        if result:

            return {
                "value": result.group(1).strip(),
                "confidence": item["confidence"],
                "source": item["text"]
            }

    return None


# find consumer care details

def find_consumer_care():

    phone = None
    email = None

    for item in ocr_data:

        text = item["text"]

        # look for a phone number

        phone_result = get_phone(text)

        if phone_result:

            phone = phone_result

        # look for an email

        email_result = get_email(text)

        if email_result:

            email = email_result

    if phone or email:

        return {
            "phone": phone,
            "email": email
        }

    return None


# ________________________________________________________________________________________________


# main function

# ________________________________________________________________________________________________


ocr = pcr(
    lang='en',
    enable_mkldnn=False
)

result = ocr.predict(
    'real2.jpeg'
)


# storing all the ocr information in one list

ocr_data = []

for res in result:

    data = res.json["res"]

    texts = data["rec_texts"]
    scores = data["rec_scores"]
    boxes = data["rec_boxes"]

    for text, score, box in zip(
        texts,
        scores,
        boxes
    ):

        ocr_data.append({

            "text": text,

            "confidence": float(score),

            "box": box

        })
# rule engine

def run_rules(data):

    # start with pass
    result = 1

    # check manufacturer
    if data["manufacturer"]:
        manufacturer_rule = 1
    else:
        manufacturer_rule = 0

    # check commodity
    if data["commodity"]:
        commodity_rule = 1
    else:
        commodity_rule = 0

    # check net quantity
    if data["net_quantity"]:
        quantity_rule = 1
    else:
        quantity_rule = 0

    # check mrp
    if data["mrp"]:
        mrp_rule = 1
    else:
        mrp_rule = 0

    # check manufacturing date
    if data["manufacturing_date"]:
        manufacturing_date_rule = 1
    else:
        manufacturing_date_rule = 0

    # check consumer care
    if data["consumer_care"]:
        consumer_care_rule = 1
    else:
        consumer_care_rule = 0

    # check country of origin
    if data["country_of_origin"]:
        country_rule = 1
    else:
        country_rule = 0

    # multiplication logic
    result = (
        manufacturer_rule
        * commodity_rule
        * quantity_rule
        * mrp_rule
        * manufacturing_date_rule
        * consumer_care_rule
        * country_rule
    )

    # final decision
    if result == 1:
        return "PASS"
    else:
        return "FAIL"

# ________________________________________________________________________________________________


# test area

# ________________________________________________________________________________________________


# print everything detected by paddleocr

print("\nxxxxxxxxxxxxxxxxxxxx ocr output xxxxxxxxxxxxxxxxxxxx\n")

for item in ocr_data:

    print(item)

# ________________________________________________________________________________________________


# extracted fields

# ________________________________________________________________________________________________


print("\n xxxxxxxxxxxxxxxxxxxx extracted fields xxxxxxxxxxxxxxxxxxxx\n")


mrp = find_mrp()

print("mrp -", mrp)


quantity = find_quantity()

print("net quantity -", quantity)


manufacturing_date = find_manufacturing_date()

print("manufacturing date -", manufacturing_date)


manufacturer = find_manufacturer()

print("manufacturer -", manufacturer)


country = find_country_of_origin()

print("country of origin -", country)


consumer_care = find_consumer_care()

print("consumer care -", consumer_care)

country = find_country_of_origin()

print("country of origin -", country)


consumer_care = find_consumer_care()

print("consumer care -", consumer_care)


commodity = find_commodity()

print("commodity -", commodity)


# structured product data for the rule engine

product_data = {
    "commodity": commodity,
    "manufacturer": manufacturer,
    "net_quantity": quantity,
    "mrp": mrp,
    "manufacturing_date": manufacturing_date,
    "country_of_origin": country,
    "consumer_care": consumer_care
}


print("\n xxxxxxxxxxxxxxxxxxxx product data xxxxxxxxxxxxxxxxxxxx\n")

for field, data in product_data.items():

    if not data:
        print(f"✗ {field}: Not detected")

    elif field == "consumer_care":

        phone = data.get("phone")
        email = data.get("email")

        if phone or email:
            print(f"✓ {field}:")

            if phone:
                print(f"    phone: {phone}")

            if email:
                print(f"    email: {email}")
        else:
            print(f"✗ {field}: Not detected")

    else:
        print(f"✓ {field}: {data['value']}")
final_result=run_rules(product_data)

print("xxxxxxxxxxxxxxxxxxxxxxxxx  Result xxxxxxxxxxxxxxxxxxxxxxx")
if final_result=="PASS":
    print("Pass")
else:
    print("Fail")

