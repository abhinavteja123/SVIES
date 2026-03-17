#!/usr/bin/env python3
"""Generate expanded mock database JSON files for SVIES project."""
import json
import os
import random

random.seed(2026)

# ─── State/UT code mapping ───────────────────────────────────────────────────
STATE_MAP = {
    "AP": "Andhra Pradesh", "AR": "Arunachal Pradesh", "AS": "Assam",
    "BR": "Bihar", "CG": "Chhattisgarh", "CH": "Chandigarh",
    "DD": "Dadra and Nagar Haveli and Daman and Diu", "DL": "Delhi",
    "GA": "Goa", "GJ": "Gujarat", "HP": "Himachal Pradesh",
    "HR": "Haryana", "JH": "Jharkhand", "JK": "Jammu and Kashmir",
    "KA": "Karnataka", "KL": "Kerala", "LA": "Ladakh",
    "LD": "Lakshadweep", "MH": "Maharashtra", "ML": "Meghalaya",
    "MN": "Manipur", "MP": "Madhya Pradesh", "MZ": "Mizoram",
    "NL": "Nagaland", "OD": "Odisha", "PB": "Punjab",
    "PY": "Puducherry", "RJ": "Rajasthan", "SK": "Sikkim",
    "TN": "Tamil Nadu", "TR": "Tripura", "TS": "Telangana",
    "UK": "Uttarakhand", "UP": "Uttar Pradesh", "WB": "West Bengal",
    "AN": "Andaman and Nicobar Islands"
}

STATE_DISTRICT_CODES = {
    "AP": [1,2,3,5,7,9,10,11,13,15,16,20,21,23,25,28,29,31,37,39],
    "AR": [1,2,3,4,5,6,7],
    "AS": [1,2,3,4,5,6,7,8,9,10,12,14],
    "BR": [1,2,3,4,5,6,7,8,10,19,21,24,38],
    "CG": [1,2,3,4,5,7,10,14,17],
    "CH": [1,2,3,4],
    "DD": [1,2,3],
    "DL": [1,2,3,4,5,6,7,8,9,10,11,12,13],
    "GA": [1,2,3,4,5,6,7,8],
    "GJ": [1,2,3,4,5,6,7,8,9,10,11,12,15,18,21,23,27],
    "HP": [1,2,3,4,5,6,7,8,10,11],
    "HR": [1,2,3,4,5,6,7,10,12,14,17,20,26,29,46,51],
    "JH": [1,2,3,4,5,6,7,8,10,14,17,19],
    "JK": [1,2,3,4,5,6,7,8,9,11,13,14,17],
    "KA": [1,2,3,4,5,6,7,9,10,11,12,14,17,19,20,34,41,50,51,53],
    "KL": [1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,17,20,39,58,59,66],
    "LA": [1,2],
    "LD": [1,2],
    "MH": [1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,17,20,31,43,46,47,48,49,50],
    "ML": [1,2,3,4,5,6,7,8],
    "MN": [1,2,3,4,5,6,7],
    "MP": [1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,17,19,34,46,49,50,65],
    "MZ": [1,2,3,4,5,6],
    "NL": [1,2,3,4,5,6,7,8],
    "OD": [1,2,3,4,5,6,7,8,9,10,12,13,14,15,16,19,21],
    "PB": [1,2,3,4,5,6,7,8,10,11,13,14,17,20,51,65],
    "PY": [1,2,3,4,5],
    "RJ": [1,2,3,4,5,6,7,8,9,10,11,12,13,14,17,19,20,23,25,27,36,45,47,51],
    "SK": [1,2,3,4,5,6],
    "TN": [1,2,3,4,5,6,7,8,9,10,11,14,18,20,22,33,37,38,39,45,54,55,56,66,72,74,78],
    "TR": [1,2,3,4,5,6,7],
    "TS": [1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,23,25,28,29],
    "UK": [1,2,3,4,5,6,7,8,9,10,11,12,13,14,17],
    "UP": [1,2,3,4,5,6,11,12,13,14,15,16,17,18,19,20,21,25,32,41,43,46,50,51,53,55,65,70,72,78,80,81],
    "WB": [1,2,3,4,5,6,7,8,9,10,11,14,18,19,22,23,24,26,27,29,31,32,33,37,39,41,44,46,47,49,52,54,55,58,59,62,63,72,73,74,75,76,77],
    "AN": [1,2,3,4]
}

# ─── Names pool ──────────────────────────────────────────────────────────────
FIRST_NAMES_MALE = [
    "Ravi", "Suresh", "Rajesh", "Venkat", "Vikram", "Amit", "Rahul", "Sachin",
    "Srinivas", "Nilesh", "Ramesh", "Karthik", "Senthil", "Bhavani", "Arun",
    "Deepak", "Naveen", "Sanjay", "Manoj", "Vikas", "Pradeep", "Anand",
    "Gopal", "Harish", "Mohan", "Ashok", "Dinesh", "Ganesh", "Jitendra",
    "Vijay", "Prakash", "Sunil", "Ajay", "Rajendra", "Girish", "Mahesh",
    "Naresh", "Pankaj", "Tarun", "Yogesh", "Umesh", "Lalit", "Chandan",
    "Brijesh", "Hemant", "Devendra", "Kamal", "Mukesh", "Omprakash", "Rajan",
    "Shankar", "Balaji", "Murali", "Raghav", "Shyam", "Krishna", "Arjun",
    "Siddhant", "Rohan", "Aarav", "Venu", "Prasad", "Jagdish", "Lakshman",
    "Surya", "Pavan", "Nitin", "Gaurav", "Manish", "Anil", "Tushar",
    "Satish", "Kishore", "Vishnu", "Bhaskar", "Ramakrishna", "Thiru",
    "Murugan", "Selvam", "Saravanan", "Gokul", "Madhav", "Varun",
    "Bibhuti", "Ranjit", "Debashish", "Subhash", "Tapan", "Pranab",
    "Dipankar", "Utpal", "Biswajit", "Soumya", "Partha", "Indrajit",
    "Tenzin", "Lobsang", "Dorji", "Jigme", "Karma", "Pema"
]

FIRST_NAMES_FEMALE = [
    "Priya", "Lakshmi", "Deepa", "Ananya", "Neha", "Pooja", "Divya",
    "Meera", "Gurpreet", "Sunita", "Kavitha", "Rani", "Sita", "Geetha",
    "Rekha", "Padma", "Savitri", "Anjali", "Bhavana", "Chandni", "Durga",
    "Fatima", "Gauri", "Indira", "Janaki", "Kamala", "Lata", "Malini",
    "Nirmala", "Pallavi", "Radha", "Sarita", "Tanuja", "Uma", "Vasudha",
    "Yasmin", "Zara", "Aarti", "Swati", "Mamta", "Ritu", "Shobha",
    "Jyoti", "Kalpana", "Asha", "Seema", "Usha", "Vanita", "Pushpa",
    "Lalitha", "Vijaya", "Sarala", "Revathi", "Mythili", "Hema", "Chitra",
    "Sudha", "Preeti", "Nandini", "Sneha", "Aishwarya", "Keerthi",
    "Sangeetha", "Archana", "Tejaswini", "Soumya"
]

LAST_NAMES = [
    "Kumar", "Singh", "Reddy", "Patil", "Nair", "Sharma", "Gupta",
    "Patel", "Meena", "Yadav", "Banerjee", "Rao", "Kulkarni", "Subramanian",
    "Devi", "Murugan", "Joshi", "Tiwari", "Kaur", "Verma", "Prasad",
    "Ghosh", "Choudhury", "Iyer", "Menon", "Pillai", "Das", "Bose",
    "Chatterjee", "Mishra", "Pandey", "Dubey", "Srivastava", "Saxena",
    "Agarwal", "Rastogi", "Chauhan", "Thakur", "Bhatt", "Jha",
    "Rathore", "Shekhawat", "Chowdhary", "Borah", "Barua", "Gogoi",
    "Saikia", "Hazarika", "Phukan", "Kalita", "Kakati",
    "Naidu", "Varma", "Murthy", "Hegde", "Gowda", "Shetty",
    "Pai", "Bhat", "Karnik", "Deshmukh", "Jadhav", "Shinde", "Pawar",
    "Sawant", "Gaikwad", "Chavan", "Kale", "Deshpande", "Wagh",
    "Mahto", "Oraon", "Munda", "Soren", "Hansda", "Hembram",
    "Lepcha", "Bhutia", "Tamang", "Sherpa", "Limboo",
    "Namgyal", "Wangchuk", "Stanzin", "Tsering",
    "Lalruatfela", "Lalhmingmawia", "Lalrintluanga", "Zonunmawia",
    "Ningombam", "Laishram", "Thangjam", "Meitei",
    "Khonglah", "Syiem", "Lyngdoh", "Nongrum",
    "Jamir", "Ao", "Lotha", "Sema",
    "Lushai", "Hmar", "Paite", "Vaiphei",
    "Dalai", "Mohapatra", "Sahu", "Behera", "Nayak", "Sethi"
]

VEHICLE_TYPES = ["CAR", "MOTORCYCLE", "SCOOTER", "AUTO", "BUS", "TRUCK",
                 "E_RICKSHAW", "TEMPO", "TRACTOR", "VAN", "SUV"]
VEHICLE_TYPE_WEIGHTS = [35, 20, 10, 5, 3, 5, 3, 3, 3, 5, 8]

MAKES_BY_TYPE = {
    "CAR": ["Maruti Suzuki Swift", "Maruti Suzuki Baleno", "Maruti Suzuki Dzire",
            "Maruti Suzuki WagonR", "Maruti Suzuki Alto", "Maruti Suzuki Ertiga",
            "Maruti Suzuki Brezza", "Hyundai i20", "Hyundai Venue", "Hyundai Verna",
            "Hyundai Grand i10", "Hyundai Aura", "Tata Altroz", "Tata Tiago",
            "Tata Tigor", "Tata Nexon", "Honda City", "Honda Amaze", "Honda Jazz",
            "Toyota Glanza", "Toyota Etios", "Kia Seltos", "Kia Sonet",
            "Kia Carens", "Volkswagen Polo", "Volkswagen Virtus", "Skoda Slavia",
            "MG Hector", "Nissan Magnite", "Renault Kwid", "Renault Kiger"],
    "MOTORCYCLE": ["Hero Splendor", "Hero HF Deluxe", "Hero Glamour", "Hero Xtreme",
                   "Bajaj Pulsar", "Bajaj CT", "Bajaj Avenger", "Bajaj Dominar",
                   "Honda Shine", "Honda Unicorn", "Honda SP 125", "Honda Hornet",
                   "TVS Apache", "TVS Star City", "TVS Raider",
                   "Royal Enfield Classic 350", "Royal Enfield Bullet 350",
                   "Royal Enfield Meteor 350", "Royal Enfield Hunter 350",
                   "Yamaha FZ", "Yamaha R15", "Yamaha MT-15",
                   "KTM Duke 200", "KTM Duke 390", "Suzuki Gixxer"],
    "SCOOTER": ["Honda Activa", "Honda Dio", "TVS Jupiter", "TVS Ntorq",
                "Suzuki Access", "Suzuki Burgman", "Bajaj Chetak",
                "Ather 450X", "Ola S1 Pro", "Hero Pleasure", "Hero Destini",
                "Yamaha Fascino", "Yamaha Aerox"],
    "AUTO": ["Bajaj RE", "Bajaj Maxima", "Piaggio Ape", "Mahindra Treo",
             "TVS King"],
    "BUS": ["Ashok Leyland Viking", "Ashok Leyland Lynx", "Tata Starbus",
            "Tata Ultra", "Eicher Skyline Pro", "BharatBenz 1617",
            "Volvo 9600", "Scania Metrolink"],
    "TRUCK": ["Tata 407", "Tata Ace", "Tata Ultra", "Tata Prima",
              "Ashok Leyland Dost", "Ashok Leyland Ecomet", "Ashok Leyland 2518",
              "Mahindra Bolero Pickup", "Eicher Pro 2049", "Eicher Pro 3015",
              "BharatBenz 1015R", "Isuzu D-Max"],
    "E_RICKSHAW": ["Lohia Comfort", "Kinetic Safar", "Mahindra Treo Zor",
                   "Piaggio Ape E-City", "YC Electric", "Goenka Electric",
                   "Saera Electric", "Mini Metro E-Rickshaw"],
    "TEMPO": ["Mahindra Bolero Pickup", "Tata Ace Gold", "Ashok Leyland Dost",
              "Piaggio Ape Xtra", "Bajaj Maxima C", "Force Traveller"],
    "TRACTOR": ["Mahindra 575 DI", "Mahindra Arjun Novo", "Massey Ferguson 1035",
                "Swaraj 744 FE", "John Deere 5310", "TAFE 45 DI",
                "Sonalika DI 60", "Eicher 380", "Kubota MU4501",
                "New Holland 3600"],
    "VAN": ["Maruti Suzuki Eeco", "Tata Winger", "Force Traveller",
            "Mahindra Supro", "Ashok Leyland Stile", "Datsun GO+"],
    "SUV": ["Tata Safari", "Tata Harrier", "Tata Punch", "Mahindra Thar",
            "Mahindra Scorpio N", "Mahindra XUV700", "Mahindra XUV300",
            "Hyundai Creta", "Hyundai Tucson", "Kia Seltos", "Kia EV6",
            "Toyota Fortuner", "Toyota Urban Cruiser", "MG Hector Plus",
            "MG Astor", "Jeep Compass", "Skoda Kushaq", "Volkswagen Taigun"]
}

COLORS = ["WHITE", "BLACK", "SILVER", "RED", "BLUE", "GREEN", "GREY", "YELLOW"]
COLOR_WEIGHTS = [30, 15, 20, 8, 8, 5, 10, 4]

YEARS = list(range(2015, 2025))

EMAIL_PROVIDERS = ["gmail.com", "yahoo.com", "outlook.com", "rediffmail.com", "hotmail.com"]


def make_email(first, last):
    provider = random.choice(EMAIL_PROVIDERS)
    style = random.randint(1, 5)
    f = first.lower().replace(" ", "")
    l = last.lower().replace(" ", "")
    if style == 1:
        return f"{f}.{l}@{provider}"
    elif style == 2:
        return f"{f}{l}{random.randint(1,99)}@{provider}"
    elif style == 3:
        return f"{f}_{l}@{provider}"
    elif style == 4:
        return f"{f}{random.randint(10,999)}@{provider}"
    else:
        return f"{f[0]}{l}@{provider}"


def make_phone():
    # Indian mobile: +91 followed by 10 digits starting with 6-9
    first_digit = random.choice([6, 7, 8, 9])
    rest = "".join([str(random.randint(0, 9)) for _ in range(9)])
    return f"+91{first_digit}{rest}"


def make_name():
    if random.random() < 0.55:
        first = random.choice(FIRST_NAMES_MALE)
    else:
        first = random.choice(FIRST_NAMES_FEMALE)
    last = random.choice(LAST_NAMES)
    return f"{first} {last}"


def make_plate(state_code):
    dist = random.choice(STATE_DISTRICT_CODES.get(state_code, [1, 2, 3]))
    letters = "".join(random.choices("ABCDEFGHJKLMNPQRSTUVWXYZ", k=2))
    num = random.randint(1000, 9999)
    return f"{state_code}{dist:02d}{letters}{num}"


def make_bh_plate(year_suffix):
    num = random.randint(1000, 9999)
    letters = "".join(random.choices("ABCDEFGHJKLMNPQRSTUVWXYZ", k=2))
    return f"{year_suffix:02d}BH{num}{letters}"


def make_vehicle_record(plate, state_code, status="ACTIVE"):
    vtype = random.choices(VEHICLE_TYPES, weights=VEHICLE_TYPE_WEIGHTS, k=1)[0]
    make = random.choice(MAKES_BY_TYPE[vtype])
    color = random.choices(COLORS, weights=COLOR_WEIGHTS, k=1)[0]
    year = random.choice(YEARS)
    name = make_name()
    state_name = STATE_MAP.get(state_code, "Bharat")

    return {
        "owner": name,
        "phone": make_phone(),
        "email": make_email(name.split()[0], name.split()[-1]),
        "vehicle_type": vtype,
        "color": color,
        "make": make,
        "year": year,
        "state": state_name,
        "registration_state_code": state_code,
        "status": status
    }


# ═══════════════════════════════════════════════════════════════════════════════
# PRESERVED PLATES (29 total) — keep exact data for those that exist
# ═══════════════════════════════════════════════════════════════════════════════

# 6 plates that exist in current file — preserve EXACT data
EXISTING_VAHAN = {
    "AP28CD1234": {
        "owner": "Suresh Reddy", "phone": "+919123456789", "email": "suresh@email.com",
        "vehicle_type": "CAR", "color": "SILVER", "make": "Hyundai i20",
        "year": 2021, "state": "Andhra Pradesh", "registration_state_code": "AP", "status": "ACTIVE"
    },
    "TS09EF1234": {
        "owner": "Ravi Kumar", "phone": "+919876543210", "email": "ravi@email.com",
        "vehicle_type": "CAR", "color": "WHITE", "make": "Maruti Swift",
        "year": 2020, "state": "Telangana", "registration_state_code": "TS", "status": "ACTIVE"
    },
    "MH02AB3333": {
        "owner": "Rajesh Patil", "phone": "+919678901234", "email": "rajesh@email.com",
        "vehicle_type": "TRUCK", "color": "BLUE", "make": "Tata 407",
        "year": 2017, "state": "Maharashtra", "registration_state_code": "MH", "status": "ACTIVE"
    },
    "TS07GH5555": {
        "owner": "Venkat Rao", "phone": "+919112233445", "email": "venkat@email.com",
        "vehicle_type": "AUTO", "color": "YELLOW", "make": "Bajaj RE",
        "year": 2018, "state": "Telangana", "registration_state_code": "TS", "status": "ACTIVE"
    },
    "22BH1234AB": {
        "owner": "Vikram Singh", "phone": "+919889900112", "email": "vikram@email.com",
        "vehicle_type": "CAR", "color": "BLACK", "make": "MG Hector",
        "year": 2023, "state": "Bharat", "registration_state_code": "BH", "status": "ACTIVE"
    },
    "MH12XY9999": {
        "owner": "TEST FAKE OWNER", "phone": "+911111111111", "email": "fake@test.com",
        "vehicle_type": "MOTORCYCLE", "color": "WHITE", "make": "Honda Activa",
        "year": 2018, "state": "Maharashtra", "registration_state_code": "MH", "status": "ACTIVE"
    }
}

# Existing PUCC data for preserved plates
EXISTING_PUCC = {
    "TS09EF1234": {"valid_until": "2026-06-01", "status": "VALID"},
    "AP28CD1234": {"valid_until": "2026-03-15", "status": "VALID"},
    "MH02AB3333": {"valid_until": "2024-03-01", "status": "EXPIRED"},
    "TS07GH5555": {"valid_until": "2024-02-01", "status": "EXPIRED"},
    "22BH1234AB": {"valid_until": "2026-08-01", "status": "VALID"},
}

# Existing insurance data for preserved plates
EXISTING_INSURANCE = {
    "TS09EF1234": {"valid_until": "2026-12-01", "type": "COMPREHENSIVE", "status": "VALID"},
    "AP28CD1234": {"valid_until": "2026-05-01", "type": "COMPREHENSIVE", "status": "VALID"},
    "MH02AB3333": {"valid_until": "2024-01-01", "type": "THIRD_PARTY", "status": "EXPIRED"},
    "TS07GH5555": {"valid_until": "2024-04-01", "type": "THIRD_PARTY", "status": "EXPIRED"},
    "22BH1234AB": {"valid_until": "2026-11-01", "type": "COMPREHENSIVE", "status": "VALID"},
}

# 23 plates that don't exist yet — create fresh data for them
NEW_PRESERVED_PLATES = {
    "AP09AB1234": {"state_code": "AP"},
    "TS08CD5678": {"state_code": "TS"},
    "MH12GH7777": {"state_code": "MH"},
    "KA01EE9999": {"state_code": "KA"},
    "TN22FF4444": {"state_code": "TN"},
    "DL01AB0001": {"state_code": "DL"},
    "GJ06KK2222": {"state_code": "GJ"},
    "RJ14LL6666": {"state_code": "RJ"},
    "UP80MM1111": {"state_code": "UP"},
    "WB26NN4444": {"state_code": "WB"},
    "MP09PP8888": {"state_code": "MP"},
    "PB10QQ5555": {"state_code": "PB"},
    "AP05JJ6789": {"state_code": "AP"},
    "KA19DD3456": {"state_code": "KA"},
    "TN01CC7890": {"state_code": "TN"},
    "DL08FF2345": {"state_code": "DL"},
    "MH20GG5678": {"state_code": "MH"},
    "GJ01HH9012": {"state_code": "GJ"},
    "RJ02II3456": {"state_code": "RJ"},
    "UP32JJ7890": {"state_code": "UP"},
    "WB10KK1234": {"state_code": "WB"},
    "MP04LL5678": {"state_code": "MP"},
    "PB08MM9012": {"state_code": "PB"},
}

# Handcraft realistic data for new preserved plates
NEW_PRESERVED_VAHAN = {
    "AP09AB1234": {
        "owner": "Venkata Ramana Reddy", "phone": "+919848012345", "email": "venkata.reddy@gmail.com",
        "vehicle_type": "CAR", "color": "WHITE", "make": "Maruti Suzuki Swift",
        "year": 2021, "state": "Andhra Pradesh", "registration_state_code": "AP", "status": "ACTIVE"
    },
    "TS08CD5678": {
        "owner": "Srinivasa Rao", "phone": "+919900123456", "email": "srinivasa.rao@gmail.com",
        "vehicle_type": "CAR", "color": "SILVER", "make": "Hyundai Venue",
        "year": 2022, "state": "Telangana", "registration_state_code": "TS", "status": "ACTIVE"
    },
    "MH12GH7777": {
        "owner": "Amol Deshmukh", "phone": "+919822334455", "email": "amol.deshmukh@gmail.com",
        "vehicle_type": "SUV", "color": "BLACK", "make": "Tata Harrier",
        "year": 2023, "state": "Maharashtra", "registration_state_code": "MH", "status": "ACTIVE"
    },
    "KA01EE9999": {
        "owner": "Raghavendra Hegde", "phone": "+919845567890", "email": "raghavendra.hegde@gmail.com",
        "vehicle_type": "CAR", "color": "RED", "make": "Honda City",
        "year": 2022, "state": "Karnataka", "registration_state_code": "KA", "status": "ACTIVE"
    },
    "TN22FF4444": {
        "owner": "Muruganantham S", "phone": "+919443112233", "email": "muruganantham@yahoo.com",
        "vehicle_type": "MOTORCYCLE", "color": "BLACK", "make": "Royal Enfield Classic 350",
        "year": 2020, "state": "Tamil Nadu", "registration_state_code": "TN", "status": "ACTIVE"
    },
    "DL01AB0001": {
        "owner": "Arun Sharma", "phone": "+919810223344", "email": "arun.sharma@outlook.com",
        "vehicle_type": "CAR", "color": "WHITE", "make": "Toyota Fortuner",
        "year": 2023, "state": "Delhi", "registration_state_code": "DL", "status": "ACTIVE"
    },
    "GJ06KK2222": {
        "owner": "Chirag Patel", "phone": "+919879445566", "email": "chirag.patel@gmail.com",
        "vehicle_type": "CAR", "color": "GREY", "make": "Kia Seltos",
        "year": 2021, "state": "Gujarat", "registration_state_code": "GJ", "status": "ACTIVE"
    },
    "RJ14LL6666": {
        "owner": "Mahaveer Shekhawat", "phone": "+919414667788", "email": "mahaveer.s@gmail.com",
        "vehicle_type": "SUV", "color": "WHITE", "make": "Mahindra Scorpio N",
        "year": 2023, "state": "Rajasthan", "registration_state_code": "RJ", "status": "ACTIVE"
    },
    "UP80MM1111": {
        "owner": "Ajay Yadav", "phone": "+919839778899", "email": "ajay.yadav99@gmail.com",
        "vehicle_type": "MOTORCYCLE", "color": "RED", "make": "Hero Splendor",
        "year": 2019, "state": "Uttar Pradesh", "registration_state_code": "UP", "status": "ACTIVE"
    },
    "WB26NN4444": {
        "owner": "Debashish Banerjee", "phone": "+919830889900", "email": "debashish.b@gmail.com",
        "vehicle_type": "CAR", "color": "SILVER", "make": "Hyundai Grand i10",
        "year": 2020, "state": "West Bengal", "registration_state_code": "WB", "status": "ACTIVE"
    },
    "MP09PP8888": {
        "owner": "Rajendra Tiwari", "phone": "+919826990011", "email": "rajendra.tiwari@gmail.com",
        "vehicle_type": "CAR", "color": "WHITE", "make": "Maruti Suzuki WagonR",
        "year": 2019, "state": "Madhya Pradesh", "registration_state_code": "MP", "status": "ACTIVE"
    },
    "PB10QQ5555": {
        "owner": "Harpreet Singh", "phone": "+919876001122", "email": "harpreet.singh@gmail.com",
        "vehicle_type": "SUV", "color": "BLACK", "make": "Mahindra XUV700",
        "year": 2022, "state": "Punjab", "registration_state_code": "PB", "status": "ACTIVE"
    },
    "AP05JJ6789": {
        "owner": "Lakshmi Narayana", "phone": "+919848223344", "email": "lakshmi.n@gmail.com",
        "vehicle_type": "SCOOTER", "color": "GREY", "make": "Honda Activa",
        "year": 2021, "state": "Andhra Pradesh", "registration_state_code": "AP", "status": "ACTIVE"
    },
    "KA19DD3456": {
        "owner": "Girish Gowda", "phone": "+919845334455", "email": "girish.gowda@gmail.com",
        "vehicle_type": "MOTORCYCLE", "color": "BLUE", "make": "TVS Apache",
        "year": 2020, "state": "Karnataka", "registration_state_code": "KA", "status": "ACTIVE"
    },
    "TN01CC7890": {
        "owner": "Saravanan Iyer", "phone": "+919443445566", "email": "saravanan.iyer@gmail.com",
        "vehicle_type": "CAR", "color": "WHITE", "make": "Maruti Suzuki Dzire",
        "year": 2022, "state": "Tamil Nadu", "registration_state_code": "TN", "status": "ACTIVE"
    },
    "DL08FF2345": {
        "owner": "Neha Gupta", "phone": "+919810556677", "email": "neha.gupta@gmail.com",
        "vehicle_type": "CAR", "color": "RED", "make": "Tata Nexon",
        "year": 2023, "state": "Delhi", "registration_state_code": "DL", "status": "ACTIVE"
    },
    "MH20GG5678": {
        "owner": "Sachin Jadhav", "phone": "+919822667788", "email": "sachin.jadhav@gmail.com",
        "vehicle_type": "TRUCK", "color": "BLUE", "make": "Ashok Leyland Dost",
        "year": 2019, "state": "Maharashtra", "registration_state_code": "MH", "status": "ACTIVE"
    },
    "GJ01HH9012": {
        "owner": "Meena Patel", "phone": "+919879778899", "email": "meena.patel@gmail.com",
        "vehicle_type": "SCOOTER", "color": "WHITE", "make": "TVS Jupiter",
        "year": 2021, "state": "Gujarat", "registration_state_code": "GJ", "status": "ACTIVE"
    },
    "RJ02II3456": {
        "owner": "Prakash Rathore", "phone": "+919414889900", "email": "prakash.rathore@gmail.com",
        "vehicle_type": "TRACTOR", "color": "RED", "make": "Massey Ferguson 1035",
        "year": 2018, "state": "Rajasthan", "registration_state_code": "RJ", "status": "ACTIVE"
    },
    "UP32JJ7890": {
        "owner": "Sunil Mishra", "phone": "+919839990011", "email": "sunil.mishra@gmail.com",
        "vehicle_type": "CAR", "color": "SILVER", "make": "Honda Amaze",
        "year": 2020, "state": "Uttar Pradesh", "registration_state_code": "UP", "status": "ACTIVE"
    },
    "WB10KK1234": {
        "owner": "Indrajit Chatterjee", "phone": "+919830001122", "email": "indrajit.c@gmail.com",
        "vehicle_type": "CAR", "color": "WHITE", "make": "Hyundai Verna",
        "year": 2022, "state": "West Bengal", "registration_state_code": "WB", "status": "ACTIVE"
    },
    "MP04LL5678": {
        "owner": "Dinesh Dubey", "phone": "+919826112233", "email": "dinesh.dubey@gmail.com",
        "vehicle_type": "VAN", "color": "WHITE", "make": "Maruti Suzuki Eeco",
        "year": 2020, "state": "Madhya Pradesh", "registration_state_code": "MP", "status": "ACTIVE"
    },
    "PB08MM9012": {
        "owner": "Manpreet Kaur", "phone": "+919876223344", "email": "manpreet.kaur@gmail.com",
        "vehicle_type": "CAR", "color": "GREY", "make": "Hyundai i20",
        "year": 2021, "state": "Punjab", "registration_state_code": "PB", "status": "ACTIVE"
    },
}


def main():
    all_plates = []
    vahan_db = {}
    pucc_db = {}
    insurance_db = {}

    # ── Step 1: Add the 6 existing preserved plates ──
    for plate, data in EXISTING_VAHAN.items():
        vahan_db[plate] = data
        all_plates.append(plate)

    # ── Step 2: Add the 23 new preserved plates ──
    for plate, data in NEW_PRESERVED_VAHAN.items():
        vahan_db[plate] = data
        all_plates.append(plate)

    # Copy existing PUCC/insurance for preserved plates
    for plate in EXISTING_PUCC:
        pucc_db[plate] = EXISTING_PUCC[plate]
    for plate in EXISTING_INSURANCE:
        insurance_db[plate] = EXISTING_INSURANCE[plate]

    # ── Step 3: Generate 11 more BH-series plates (total 12 with 22BH1234AB) ──
    bh_years = [20, 21, 22, 23, 24, 20, 21, 22, 23, 24, 23]
    bh_plates_generated = set()
    for yr in bh_years:
        while True:
            bp = make_bh_plate(yr)
            if bp not in bh_plates_generated and bp not in vahan_db:
                break
        bh_plates_generated.add(bp)
        rec = make_vehicle_record(bp, "BH")
        rec["state"] = "Bharat"
        rec["registration_state_code"] = "BH"
        vahan_db[bp] = rec
        all_plates.append(bp)

    # ── Step 4: Ensure all 36 state codes are represented ──
    # States already covered by preserved plates
    covered_states = set()
    for plate in all_plates:
        if "BH" in plate and plate[2:4] == "BH":
            covered_states.add("BH")
        else:
            for sc in STATE_MAP:
                if plate.startswith(sc):
                    covered_states.add(sc)
                    break

    missing_states = set(STATE_MAP.keys()) - covered_states
    for sc in sorted(missing_states):
        while True:
            p = make_plate(sc)
            if p not in vahan_db:
                break
        vahan_db[p] = make_vehicle_record(p, sc)
        all_plates.append(p)

    # ── Step 5: Fill remaining to reach 200 ──
    remaining = 200 - len(all_plates)
    # Distribute across states weighted by population roughly
    high_pop_states = ["MH", "UP", "TN", "KA", "DL", "GJ", "RJ", "AP", "TS", "WB", "MP", "HR", "PB", "KL", "BR", "JH", "OD", "CG", "UK", "AS"]

    for i in range(remaining):
        sc = random.choice(high_pop_states)
        while True:
            p = make_plate(sc)
            if p not in vahan_db:
                break
        # Assign status
        r = random.random()
        if r < 0.03:
            status = "BLACKLISTED"
        elif r < 0.10:
            status = "SUSPENDED"
        else:
            status = "ACTIVE"
        vahan_db[p] = make_vehicle_record(p, sc, status)
        all_plates.append(p)

    # ── Step 6: Generate PUCC data for all plates ──
    for plate in all_plates:
        if plate in pucc_db:
            continue  # Already have preserved data
        r = random.random()
        if r < 0.20:
            # Expired
            y = random.randint(2023, 2025)
            m = random.randint(1, 3 if y == 2025 else 12)
            pucc_db[plate] = {
                "valid_until": f"{y}-{m:02d}-{random.choice(['01','15'])}",
                "status": "EXPIRED"
            }
        else:
            y = random.choice([2025, 2026, 2027])
            if y == 2025:
                m = random.randint(6, 12)
            elif y == 2026:
                m = random.randint(1, 12)
            else:
                m = random.randint(1, 12)
            pucc_db[plate] = {
                "valid_until": f"{y}-{m:02d}-{random.choice(['01','15'])}",
                "status": "VALID"
            }

    # Also add PUCC for MH12XY9999 if not present
    if "MH12XY9999" not in pucc_db:
        pucc_db["MH12XY9999"] = {"valid_until": "2026-09-01", "status": "VALID"}

    # ── Step 7: Generate Insurance data for all plates ──
    for plate in all_plates:
        if plate in insurance_db:
            continue  # Already have preserved data
        r = random.random()
        ins_type = "COMPREHENSIVE" if random.random() < 0.70 else "THIRD_PARTY"
        if r < 0.15:
            # Expired
            y = random.randint(2023, 2025)
            m = random.randint(1, 3 if y == 2025 else 12)
            insurance_db[plate] = {
                "valid_until": f"{y}-{m:02d}-{random.choice(['01','15'])}",
                "type": ins_type,
                "status": "EXPIRED"
            }
        else:
            y = random.choice([2025, 2026, 2027])
            if y == 2025:
                m = random.randint(6, 12)
            elif y == 2026:
                m = random.randint(1, 12)
            else:
                m = random.randint(1, 12)
            insurance_db[plate] = {
                "valid_until": f"{y}-{m:02d}-{random.choice(['01','15'])}",
                "type": ins_type,
                "status": "VALID"
            }

    # Also add insurance for MH12XY9999 if not present
    if "MH12XY9999" not in insurance_db:
        insurance_db["MH12XY9999"] = {"valid_until": "2026-09-01", "type": "COMPREHENSIVE", "status": "VALID"}

    # ── Step 8: Generate Stolen list ──
    original_stolen = ["AP28CD1234", "TS07GH5555", "MH02AB3333"]
    # Pick 9 more from the non-preserved new plates
    non_preserved_plates = [p for p in all_plates if p not in set(list(EXISTING_VAHAN.keys()) + list(NEW_PRESERVED_VAHAN.keys()))]
    extra_stolen = random.sample(non_preserved_plates, 9)
    stolen_list = original_stolen + extra_stolen

    stolen_db = {
        "stolen_plates": stolen_list,
        "last_updated": "2026-03-14"
    }

    # ── Step 9: Reorder vahan to put preserved plates first ──
    preserved_order = [
        "AP09AB1234", "TS08CD5678", "MH12GH7777", "KA01EE9999", "TN22FF4444",
        "DL01AB0001", "AP28CD1234", "TS09EF1234", "MH02AB3333", "GJ06KK2222",
        "RJ14LL6666", "UP80MM1111", "WB26NN4444", "MP09PP8888", "PB10QQ5555",
        "TS07GH5555", "AP05JJ6789", "KA19DD3456", "TN01CC7890", "DL08FF2345",
        "MH20GG5678", "GJ01HH9012", "RJ02II3456", "UP32JJ7890", "WB10KK1234",
        "MP04LL5678", "PB08MM9012", "22BH1234AB", "MH12XY9999"
    ]

    ordered_vahan = {}
    ordered_pucc = {}
    ordered_insurance = {}

    # Preserved plates first
    for p in preserved_order:
        if p in vahan_db:
            ordered_vahan[p] = vahan_db[p]
        if p in pucc_db:
            ordered_pucc[p] = pucc_db[p]
        if p in insurance_db:
            ordered_insurance[p] = insurance_db[p]

    # Then the rest
    for p in all_plates:
        if p not in ordered_vahan and p in vahan_db:
            ordered_vahan[p] = vahan_db[p]
        if p not in ordered_pucc and p in pucc_db:
            ordered_pucc[p] = pucc_db[p]
        if p not in ordered_insurance and p in insurance_db:
            ordered_insurance[p] = insurance_db[p]

    # ── Step 10: Write files ──
    script_dir = os.path.dirname(os.path.abspath(__file__))

    with open(os.path.join(script_dir, "vahan.json"), "w", encoding="utf-8") as f:
        json.dump(ordered_vahan, f, indent=2, ensure_ascii=False)

    with open(os.path.join(script_dir, "pucc.json"), "w", encoding="utf-8") as f:
        json.dump(ordered_pucc, f, indent=2, ensure_ascii=False)

    with open(os.path.join(script_dir, "insurance.json"), "w", encoding="utf-8") as f:
        json.dump(ordered_insurance, f, indent=2, ensure_ascii=False)

    with open(os.path.join(script_dir, "stolen.json"), "w", encoding="utf-8") as f:
        json.dump(stolen_db, f, indent=2, ensure_ascii=False)

    # ── Validation ──
    print(f"vahan.json:     {len(ordered_vahan)} records")
    print(f"pucc.json:      {len(ordered_pucc)} records")
    print(f"insurance.json: {len(ordered_insurance)} records")
    print(f"stolen.json:    {len(stolen_db['stolen_plates'])} stolen plates")

    # Check all 36 states
    state_codes_found = set()
    for p, rec in ordered_vahan.items():
        state_codes_found.add(rec["registration_state_code"])
    non_bh_states = state_codes_found - {"BH"}
    missing = set(STATE_MAP.keys()) - non_bh_states
    print(f"State codes covered: {len(non_bh_states)}/36")
    if missing:
        print(f"  MISSING: {missing}")
    else:
        print("  All 36 state codes present!")

    # BH plates count
    bh_count = sum(1 for p in ordered_vahan if ordered_vahan[p].get("registration_state_code") == "BH")
    print(f"BH-series plates: {bh_count}")

    # Check preserved plates
    for p in preserved_order:
        if p not in ordered_vahan:
            print(f"  WARNING: Preserved plate {p} missing from vahan!")
        if p not in ordered_pucc:
            print(f"  WARNING: Preserved plate {p} missing from pucc!")
        if p not in ordered_insurance:
            print(f"  WARNING: Preserved plate {p} missing from insurance!")

    # Check stolen
    for sp in stolen_db["stolen_plates"]:
        if sp not in ordered_vahan:
            print(f"  WARNING: Stolen plate {sp} not in vahan!")

    # Count expired
    pucc_expired = sum(1 for v in ordered_pucc.values() if v["status"] == "EXPIRED")
    ins_expired = sum(1 for v in ordered_insurance.values() if v["status"] == "EXPIRED")
    print(f"PUCC expired: {pucc_expired}/{len(ordered_pucc)} ({100*pucc_expired/len(ordered_pucc):.1f}%)")
    print(f"Insurance expired: {ins_expired}/{len(ordered_insurance)} ({100*ins_expired/len(ordered_insurance):.1f}%)")

    # Consistency check
    vahan_plates = set(ordered_vahan.keys())
    pucc_plates = set(ordered_pucc.keys())
    ins_plates = set(ordered_insurance.keys())
    if vahan_plates == pucc_plates == ins_plates:
        print("All plates consistent across all files!")
    else:
        print(f"  INCONSISTENCY: vahan={len(vahan_plates)}, pucc={len(pucc_plates)}, ins={len(ins_plates)}")
        print(f"  In vahan but not pucc: {vahan_plates - pucc_plates}")
        print(f"  In vahan but not ins:  {vahan_plates - ins_plates}")


if __name__ == "__main__":
    main()
