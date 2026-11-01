from sqlalchemy.orm import Session

from app.models import Household, Member, Recipe, WeeklyMenu


def _ing(name: str, qty: float, unit: str, category: str) -> dict:
    return {"name": name, "qty": qty, "unit": unit, "category": category}


RECIPES: list[dict] = [
    {
        "name": "Poha",
        "name_hi": "पोहा",
        "meal_types": ["breakfast"],
        "tags": ["veg", "quick"],
        "ingredients": [
            _ing("poha", 250, "g", "grains"),
            _ing("onion", 1, "pcs", "vegetables"),
            _ing("potato", 1, "pcs", "vegetables"),
            _ing("peanuts", 40, "g", "dry_goods"),
            _ing("mustard seeds", 1, "tsp", "spices"),
            _ing("turmeric", 0.5, "tsp", "spices"),
            _ing("lemon", 1, "pcs", "vegetables"),
            _ing("coriander", 10, "g", "vegetables"),
        ],
        "instructions": "Rinse poha, temper mustard seeds, saute onion and potato, mix poha with turmeric.",
        "hindi_script": "Aaj nashta poha banana hai. Poha dho kar, rai aur pyaaz aloo ke saath pakao.",
    },
    {
        "name": "Upma",
        "name_hi": "उपमा",
        "meal_types": ["breakfast"],
        "tags": ["veg"],
        "ingredients": [
            _ing("rava", 200, "g", "grains"),
            _ing("onion", 1, "pcs", "vegetables"),
            _ing("carrot", 1, "pcs", "vegetables"),
            _ing("green chilli", 2, "pcs", "vegetables"),
            _ing("mustard seeds", 1, "tsp", "spices"),
            _ing("ghee", 2, "tbsp", "dairy"),
        ],
        "instructions": "Roast rava, temper spices and vegetables, add water and cook until fluffy.",
        "hindi_script": "Nashta upma hai. Sooji bhun ke sabzi ke saath pakao.",
    },
    {
        "name": "Aloo Paratha",
        "name_hi": "आलू पराठा",
        "meal_types": ["breakfast", "dinner"],
        "tags": ["veg"],
        "ingredients": [
            _ing("wheat flour", 400, "g", "grains"),
            _ing("potato", 4, "pcs", "vegetables"),
            _ing("green chilli", 2, "pcs", "vegetables"),
            _ing("coriander", 15, "g", "vegetables"),
            _ing("ghee", 4, "tbsp", "dairy"),
            _ing("curd", 200, "g", "dairy"),
        ],
        "instructions": "Stuff spiced mashed potato in wheat dough, roast with ghee. Serve with curd.",
        "hindi_script": "Aloo paratha banana hai, dahi ke saath serve karna.",
    },
    {
        "name": "Idli Sambar",
        "name_hi": "इडली सांभर",
        "meal_types": ["breakfast"],
        "tags": ["veg", "south"],
        "ingredients": [
            _ing("idli batter", 800, "ml", "grains"),
            _ing("toor dal", 150, "g", "pulses"),
            _ing("sambar powder", 2, "tbsp", "spices"),
            _ing("tamarind", 20, "g", "dry_goods"),
            _ing("onion", 1, "pcs", "vegetables"),
            _ing("tomato", 2, "pcs", "vegetables"),
            _ing("coconut chutney", 150, "g", "other"),
        ],
        "instructions": "Steam idli. Cook toor dal sambar with vegetables. Serve with chutney.",
        "hindi_script": "Idli steam karo aur sambar coconut chutney ke saath do.",
    },
    {
        "name": "Masala Dosa",
        "name_hi": "मसाला डोसा",
        "meal_types": ["breakfast", "dinner"],
        "tags": ["veg", "weekend"],
        "ingredients": [
            _ing("dosa batter", 800, "ml", "grains"),
            _ing("potato", 4, "pcs", "vegetables"),
            _ing("onion", 2, "pcs", "vegetables"),
            _ing("coconut chutney", 150, "g", "other"),
            _ing("sambar powder", 1, "tbsp", "spices"),
        ],
        "instructions": "Spread dosa, fill with potato masala, serve with chutney.",
        "hindi_script": "Masala dosa banana hai, aloo masala bhar ke.",
    },
    {
        "name": "Dal Tadka with Rice",
        "name_hi": "दाल तड़का चावल",
        "meal_types": ["lunch", "dinner"],
        "tags": ["veg", "everyday"],
        "ingredients": [
            _ing("toor dal", 200, "g", "pulses"),
            _ing("rice", 400, "g", "grains"),
            _ing("onion", 1, "pcs", "vegetables"),
            _ing("tomato", 2, "pcs", "vegetables"),
            _ing("ghee", 2, "tbsp", "dairy"),
            _ing("cumin", 1, "tsp", "spices"),
            _ing("garlic", 6, "cloves", "vegetables"),
            _ing("turmeric", 0.5, "tsp", "spices"),
        ],
        "instructions": "Cook dal, temper with ghee cumin garlic. Serve with steamed rice.",
        "hindi_script": "Dal tadka aur chawal banana hai. Tadka ghee jeera lehsun se lagana.",
    },
    {
        "name": "Rajma Chawal",
        "name_hi": "राजमा चावल",
        "meal_types": ["lunch"],
        "tags": ["veg", "north"],
        "ingredients": [
            _ing("rajma", 300, "g", "pulses"),
            _ing("rice", 400, "g", "grains"),
            _ing("onion", 2, "pcs", "vegetables"),
            _ing("tomato", 3, "pcs", "vegetables"),
            _ing("ginger garlic paste", 2, "tbsp", "other"),
            _ing("rajma masala", 1, "tbsp", "spices"),
        ],
        "instructions": "Soak and pressure cook rajma, simmer in onion tomato gravy, serve with rice.",
        "hindi_script": "Rajma chawal banana hai. Rajma achhe se galne chahiye.",
    },
    {
        "name": "Chole Bhature",
        "name_hi": "छोले भटूरे",
        "meal_types": ["lunch", "brunch"],
        "tags": ["veg", "weekend"],
        "ingredients": [
            _ing("chickpeas", 300, "g", "pulses"),
            _ing("maida", 400, "g", "grains"),
            _ing("yogurt", 80, "g", "dairy"),
            _ing("onion", 2, "pcs", "vegetables"),
            _ing("tomato", 3, "pcs", "vegetables"),
            _ing("chole masala", 2, "tbsp", "spices"),
            _ing("oil", 200, "ml", "other"),
        ],
        "instructions": "Cook spiced chickpeas. Ferment bhature dough and fry.",
        "hindi_script": "Chole bhature weekend special banana hai.",
    },
    {
        "name": "Paneer Butter Masala",
        "name_hi": "पनीर बटर मसाला",
        "meal_types": ["lunch", "dinner"],
        "tags": ["veg"],
        "ingredients": [
            _ing("paneer", 400, "g", "dairy"),
            _ing("tomato", 4, "pcs", "vegetables"),
            _ing("butter", 40, "g", "dairy"),
            _ing("cream", 80, "ml", "dairy"),
            _ing("cashew", 30, "g", "dry_goods"),
            _ing("kasuri methi", 1, "tsp", "spices"),
            _ing("roti", 8, "pcs", "grains"),
        ],
        "instructions": "Make buttery tomato cashew gravy, add paneer cubes. Serve with roti.",
        "hindi_script": "Paneer butter masala aur roti banana hai.",
    },
    {
        "name": "Mixed Vegetable Sabzi",
        "name_hi": "मिक्स्ड सब्जी",
        "meal_types": ["lunch", "dinner"],
        "tags": ["veg", "everyday"],
        "ingredients": [
            _ing("potato", 2, "pcs", "vegetables"),
            _ing("cauliflower", 300, "g", "vegetables"),
            _ing("peas", 100, "g", "vegetables"),
            _ing("carrot", 2, "pcs", "vegetables"),
            _ing("onion", 1, "pcs", "vegetables"),
            _ing("tomato", 2, "pcs", "vegetables"),
            _ing("roti", 8, "pcs", "grains"),
        ],
        "instructions": "Saute mixed vegetables with onion tomato masala. Serve with roti.",
        "hindi_script": "Mix veg sabzi aur roti banana hai.",
    },
    {
        "name": "Chicken Curry",
        "name_hi": "चिकन करी",
        "meal_types": ["lunch", "dinner"],
        "tags": ["nonveg"],
        "ingredients": [
            _ing("chicken", 800, "g", "protein"),
            _ing("onion", 3, "pcs", "vegetables"),
            _ing("tomato", 3, "pcs", "vegetables"),
            _ing("yogurt", 80, "g", "dairy"),
            _ing("ginger garlic paste", 2, "tbsp", "other"),
            _ing("chicken masala", 2, "tbsp", "spices"),
            _ing("rice", 400, "g", "grains"),
        ],
        "instructions": "Marinate chicken, cook onion tomato gravy, simmer until tender. Serve with rice.",
        "hindi_script": "Chicken curry aur chawal banana hai. Masala achha bhunna.",
    },
    {
        "name": "Egg Curry",
        "name_hi": "अंडा करी",
        "meal_types": ["lunch", "dinner"],
        "tags": ["nonveg"],
        "ingredients": [
            _ing("eggs", 8, "pcs", "protein"),
            _ing("onion", 2, "pcs", "vegetables"),
            _ing("tomato", 2, "pcs", "vegetables"),
            _ing("coconut milk", 150, "ml", "other"),
            _ing("rice", 350, "g", "grains"),
        ],
        "instructions": "Boil eggs, simmer in onion tomato coconut gravy.",
        "hindi_script": "Anda curry chawal ke saath banana hai.",
    },
    {
        "name": "Khichdi",
        "name_hi": "खिचड़ी",
        "meal_types": ["lunch", "dinner"],
        "tags": ["veg", "light"],
        "ingredients": [
            _ing("rice", 250, "g", "grains"),
            _ing("moong dal", 150, "g", "pulses"),
            _ing("ghee", 2, "tbsp", "dairy"),
            _ing("cumin", 1, "tsp", "spices"),
            _ing("turmeric", 0.5, "tsp", "spices"),
            _ing("peas", 50, "g", "vegetables"),
        ],
        "instructions": "Cook rice and moong dal together with turmeric. Temper with ghee cumin.",
        "hindi_script": "Moong dal khichdi banana hai, ghee tadka ke saath.",
    },
    {
        "name": "Veg Pulao",
        "name_hi": "वेज पुलाव",
        "meal_types": ["lunch", "dinner"],
        "tags": ["veg"],
        "ingredients": [
            _ing("basmati rice", 400, "g", "grains"),
            _ing("mixed vegetables", 300, "g", "vegetables"),
            _ing("ghee", 2, "tbsp", "dairy"),
            _ing("whole spices", 1, "tbsp", "spices"),
            _ing("raita", 200, "g", "dairy"),
        ],
        "instructions": "Saute vegetables and spices, cook basmati until fluffy. Serve with raita.",
        "hindi_script": "Veg pulao aur raita banana hai.",
    },
    {
        "name": "Palak Paneer",
        "name_hi": "पालक पनीर",
        "meal_types": ["lunch", "dinner"],
        "tags": ["veg"],
        "ingredients": [
            _ing("spinach", 400, "g", "vegetables"),
            _ing("paneer", 300, "g", "dairy"),
            _ing("onion", 1, "pcs", "vegetables"),
            _ing("garlic", 6, "cloves", "vegetables"),
            _ing("cream", 40, "ml", "dairy"),
            _ing("roti", 8, "pcs", "grains"),
        ],
        "instructions": "Blanch spinach, blend, cook with spices and paneer.",
        "hindi_script": "Palak paneer aur roti banana hai.",
    },
    {
        "name": "Samosa and Chai",
        "name_hi": "समोसा चाय",
        "meal_types": ["evening_snack"],
        "tags": ["veg", "weekend"],
        "ingredients": [
            _ing("samosa", 8, "pcs", "other"),
            _ing("tea leaves", 10, "g", "dry_goods"),
            _ing("milk", 500, "ml", "dairy"),
            _ing("sugar", 40, "g", "dry_goods"),
        ],
        "instructions": "Serve hot samosa with masala chai.",
        "hindi_script": "Shaam ko samosa aur chai ready rakhni hai.",
    },
    {
        "name": "Pakora",
        "name_hi": "पकोड़ा",
        "meal_types": ["evening_snack"],
        "tags": ["veg"],
        "ingredients": [
            _ing("besan", 200, "g", "grains"),
            _ing("onion", 2, "pcs", "vegetables"),
            _ing("potato", 2, "pcs", "vegetables"),
            _ing("oil", 250, "ml", "other"),
            _ing("green chutney", 80, "g", "other"),
        ],
        "instructions": "Make besan batter, fry onion potato pakoras.",
        "hindi_script": "Pakore talne hain, hari chutney ke saath.",
    },
    {
        "name": "Pasta Arrabbiata",
        "name_hi": "पास्ता",
        "meal_types": ["lunch", "dinner"],
        "tags": ["veg", "weekend"],
        "ingredients": [
            _ing("pasta", 400, "g", "grains"),
            _ing("tomato", 4, "pcs", "vegetables"),
            _ing("garlic", 6, "cloves", "vegetables"),
            _ing("olive oil", 2, "tbsp", "other"),
            _ing("chilli flakes", 1, "tsp", "spices"),
            _ing("cheese", 50, "g", "dairy"),
        ],
        "instructions": "Boil pasta, toss in spicy tomato garlic sauce.",
        "hindi_script": "Pasta arrabbiata banana hai, thoda spicy.",
    },
    {
        "name": "Veg Biryani",
        "name_hi": "वेज बिरयानी",
        "meal_types": ["lunch", "dinner"],
        "tags": ["veg", "weekend"],
        "ingredients": [
            _ing("basmati rice", 400, "g", "grains"),
            _ing("mixed vegetables", 400, "g", "vegetables"),
            _ing("yogurt", 100, "g", "dairy"),
            _ing("biryani masala", 2, "tbsp", "spices"),
            _ing("fried onion", 80, "g", "vegetables"),
            _ing("mint", 20, "g", "vegetables"),
        ],
        "instructions": "Layer marinated vegetables with half-cooked rice and dum cook.",
        "hindi_script": "Veg biryani dum pe banana hai.",
    },
    {
        "name": "Oats and Fruit",
        "name_hi": "ओट्स फ्रूट",
        "meal_types": ["breakfast"],
        "tags": ["veg", "light"],
        "ingredients": [
            _ing("oats", 160, "g", "grains"),
            _ing("milk", 500, "ml", "dairy"),
            _ing("banana", 2, "pcs", "vegetables"),
            _ing("honey", 2, "tbsp", "dry_goods"),
        ],
        "instructions": "Cook oats in milk, top with banana and honey.",
        "hindi_script": "Light nashta oats aur fruit ka hai.",
    },
]


def seed_if_empty(db: Session) -> None:
    if db.query(Household).count() == 0:
        household = Household(
            name="Sharma Household",
            size=4,
            weekday_meals=["breakfast", "lunch", "dinner"],
            weekend_meals=["breakfast", "lunch", "evening_snack", "dinner"],
            grocery_reminder_days=2,
            chef_call_time="07:00",
        )
        db.add(household)
        db.flush()
        db.add_all(
            [
                Member(
                    household_id=household.id,
                    name="Shubh",
                    role="admin",
                    phone="+919229247588",
                    whatsapp_phone="+919229247588",
                    notify=True,
                ),
                Member(
                    household_id=household.id,
                    name="Rishu",
                    role="member",
                    phone="919800000002",
                    whatsapp_phone="919800000002",
                    notify=True,
                ),
                Member(
                    household_id=household.id,
                    name="Bhaiya (Cook)",
                    role="cook",
                    phone="+919229247588",
                    whatsapp_phone="+919229247588",
                    notify=False,
                    is_cook=True,
                ),
            ]
        )

    if db.query(Recipe).count() == 0:
        for item in RECIPES:
            db.add(
                Recipe(
                    name=item["name"],
                    name_hi=item["name_hi"],
                    meal_types=item["meal_types"],
                    tags=item["tags"],
                    ingredients=item["ingredients"],
                    instructions=item["instructions"],
                    hindi_script=item["hindi_script"],
                )
            )
    db.commit()
    if db.query(WeeklyMenu).count() == 0:
        from app.services.grocery import build_shopping_list
        from app.services.menu import generate_weekly_menu
        from app.services.timeutil import today

        menu = generate_weekly_menu(db, today(), source="seed")
        build_shopping_list(db, menu.week_start)
