import streamlit as st
import pandas as pd
from datetime import date, timedelta
from pathlib import Path

# ---------------------------------------------------------
# Smart Food Waste & Menu Tracker
# A smart food management system to reduce food wastage
# ---------------------------------------------------------

st.set_page_config(
    page_title="Smart Food Waste & Menu Tracker",
    page_icon="🌱",
    layout="wide"
)

DATA_DIR = Path(__file__).parent / "ecoplate_data"
DATA_DIR.mkdir(exist_ok=True)

INVENTORY_FILE = DATA_DIR / "inventory.csv"
WASTE_FILE = DATA_DIR / "waste_log.csv"

INVENTORY_COLUMNS = [
    "id", "food", "category", "quantity", "unit",
    "expiry_date", "added_date"
]
WASTE_COLUMNS = [
    "date", "food", "quantity", "unit", "reason"
]


def load_data(file_path, columns):
    """Load a CSV file, or return an empty table with the expected columns."""
    if file_path.exists():
        try:
            df = pd.read_csv(file_path)
            for column in columns:
                if column not in df.columns:
                    df[column] = ""
            return df[columns]
        except Exception:
            st.warning(f"Could not read {file_path.name}. Starting with an empty table.")
    return pd.DataFrame(columns=columns)


def save_data(df, file_path):
    """Save a table to the project's local data folder."""
    df.to_csv(file_path, index=False)


def next_id(df):
    if df.empty or "id" not in df.columns:
        return 1
    numeric_ids = pd.to_numeric(df["id"], errors="coerce").dropna()
    return int(numeric_ids.max()) + 1 if not numeric_ids.empty else 1


def safe_number(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


inventory = load_data(INVENTORY_FILE, INVENTORY_COLUMNS)
waste = load_data(WASTE_FILE, WASTE_COLUMNS)

# Normalize date columns so comparisons work reliably.
if not inventory.empty:
    inventory["expiry_date"] = pd.to_datetime(
        inventory["expiry_date"], errors="coerce"
    ).dt.date
    inventory["added_date"] = pd.to_datetime(
        inventory["added_date"], errors="coerce"
    ).dt.date

if not waste.empty:
    waste["date"] = pd.to_datetime(waste["date"], errors="coerce").dt.date

# ------------------------- Sidebar -------------------------

st.sidebar.title("🌱 Smart Food Waste & Menu Tracker")
st.sidebar.caption("Smart Food Waste Management System")
page = st.sidebar.radio(
    "Navigate",
    [
        "Dashboard",
        "Food Inventory",
        "Expiry Tracker",
        "Smart Menu Planner",
        "Waste Log",
        "About Project"
    ]
)

st.sidebar.divider()
st.sidebar.info(
    "Project tip: Add a few food items in Food Inventory first. "
    "The dashboard and menu planner will then use your data."
)

# ------------------------- Dashboard -------------------------

if page == "Dashboard":
    st.title("🌱 Smart Food Waste & Menu Tracker")
    st.write("Monitor food inventory, reduce waste, and make smarter meal plans.")

    today = date.today()

    total_items = len(inventory)
    total_quantity = (
        pd.to_numeric(inventory["quantity"], errors="coerce").fillna(0).sum()
        if not inventory.empty else 0
    )
    total_waste = (
        pd.to_numeric(waste["quantity"], errors="coerce").fillna(0).sum()
        if not waste.empty else 0
    )

    expiring_soon = 0
    expired_count = 0
    if not inventory.empty:
        days_left = inventory["expiry_date"].apply(
            lambda d: (d - today).days if pd.notna(d) else 99999
        )
        expiring_soon = int(((days_left >= 0) & (days_left <= 3)).sum())
        expired_count = int((days_left < 0).sum())

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Food items", total_items)
    c2.metric("Quantity in stock", f"{total_quantity:g}")
    c3.metric("Items expiring in 3 days", expiring_soon)
    c4.metric("Total quantity wasted", f"{total_waste:g}")

    st.subheader("Expiry overview")
    if inventory.empty:
        st.info("Your inventory is empty. Add food items in the Food Inventory page.")
    else:
        overview = inventory.copy()
        overview["Days left"] = overview["expiry_date"].apply(
            lambda d: (d - today).days if pd.notna(d) else None
        )
        overview["Status"] = overview["Days left"].apply(
            lambda n: "Expired" if n is not None and n < 0
            else "Use soon" if n is not None and n <= 3
            else "Fresh"
        )
        st.dataframe(
            overview[["food", "category", "quantity", "unit",
                      "expiry_date", "Days left", "Status"]],
            use_container_width=True,
            hide_index=True
        )

    st.subheader("Food waste trend")
    if waste.empty:
        st.info("No waste entries yet. Record wasted food in the Waste Log page.")
    else:
        chart_data = waste.copy()
        chart_data["quantity"] = pd.to_numeric(
            chart_data["quantity"], errors="coerce"
        ).fillna(0)
        daily = chart_data.groupby("date", as_index=False)["quantity"].sum()
        daily = daily.sort_values("date")
        st.line_chart(daily.set_index("date")["quantity"])

    st.caption(
        "Environmental impact figures are estimates for demonstration, "
        "not measured scientific results."
    )

# ------------------------- Food Inventory -------------------------

elif page == "Food Inventory":
    st.title("🧺 Food Inventory")
    st.write("Add food items you currently have and keep track of their expiry dates.")

    with st.form("add_food_form", clear_on_submit=True):
        st.subheader("Add a food item")
        col1, col2 = st.columns(2)
        food_name = col1.text_input("Food name", placeholder="Example: Tomatoes")
        category = col2.selectbox(
            "Category",
            ["Vegetables", "Fruits", "Dairy", "Grains", "Protein",
             "Bakery", "Canned food", "Other"]
        )
        col3, col4, col5 = st.columns(3)
        quantity = col3.number_input("Quantity", min_value=0.01, value=1.0, step=0.5)
        unit = col4.selectbox("Unit", ["kg", "g", "litre", "ml", "pieces", "packets"])
        expiry = col5.date_input("Expiry date", value=date.today() + timedelta(days=5))
        submitted = st.form_submit_button("Add to inventory")

        if submitted:
            if not food_name.strip():
                st.error("Please enter a food name.")
            else:
                new_row = {
                    "id": next_id(inventory),
                    "food": food_name.strip(),
                    "category": category,
                    "quantity": quantity,
                    "unit": unit,
                    "expiry_date": expiry,
                    "added_date": date.today()
                }
                inventory = pd.concat(
                    [inventory, pd.DataFrame([new_row])],
                    ignore_index=True
                )
                save_data(inventory, INVENTORY_FILE)
                st.success(f"{food_name.strip()} added successfully.")
                st.rerun()

    st.subheader("Current inventory")
    if inventory.empty:
        st.info("No food items have been added yet.")
    else:
        display_inventory = inventory.copy()
        display_inventory["expiry_date"] = display_inventory["expiry_date"].astype(str)
        display_inventory["added_date"] = display_inventory["added_date"].astype(str)
        st.dataframe(
            display_inventory[["id", "food", "category", "quantity",
                               "unit", "expiry_date"]],
            use_container_width=True,
            hide_index=True
        )

        item_ids = pd.to_numeric(inventory["id"], errors="coerce").dropna().astype(int).tolist()
        selected_id = st.selectbox("Select an item ID to remove", item_ids)
        if st.button("Remove selected item"):
            inventory = inventory[
                pd.to_numeric(inventory["id"], errors="coerce") != selected_id
            ].copy()
            save_data(inventory, INVENTORY_FILE)
            st.success("Item removed.")
            st.rerun()

# ------------------------- Expiry Tracker -------------------------

elif page == "Expiry Tracker":
    st.title("⏰ Expiry Date Tracker")
    st.write("Find food that should be used soon.")

    if inventory.empty:
        st.info("Add food items in Food Inventory to use the expiry tracker.")
    else:
        tracker = inventory.copy()
        today = date.today()
        tracker["days_left"] = tracker["expiry_date"].apply(
            lambda d: (d - today).days if pd.notna(d) else None
        )

        def expiry_status(days):
            if days is None:
                return "Date not set"
            if days < 0:
                return "Expired"
            if days == 0:
                return "Expires today"
            if days <= 3:
                return "Use soon"
            return "Fresh"

        tracker["status"] = tracker["days_left"].apply(expiry_status)
        tracker = tracker.sort_values("days_left", na_position="last")

        for _, row in tracker.iterrows():
            days = row["days_left"]
            label = f"{row['food']} — {row['quantity']} {row['unit']} — {row['expiry_date']}"
            if days is not None and days < 0:
                st.error(f"⚠️ {label} — expired {abs(days)} day(s) ago. Check food safety before use.")
            elif days == 0:
                st.warning(f"⏳ {label} — expires today.")
            elif days is not None and days <= 3:
                st.warning(f"⏳ {label} — {days} day(s) left. Consider using it soon.")
            else:
                st.success(f"✅ {label} — {row['status']}")

        st.caption(
            "The tracker is a reminder only. Always check food condition and "
            "follow food-safety guidance; do not use food just because it appears here."
        )

# ------------------------- Smart Menu Planner -------------------------

elif page == "Smart Menu Planner":
    st.title("🍲 Smart Menu Planner")
    st.write(
        "Get simple meal ideas based on ingredients in your inventory. "
        "Suggestions use a built-in rule-based demo, not an external AI service."
    )

    if inventory.empty:
        st.info("Add ingredients in Food Inventory to receive menu suggestions.")
    else:
        available_foods = inventory["food"].dropna().astype(str).tolist()
        normalized = {item.lower().strip() for item in available_foods}

        recipe_ideas = [
            {
                "name": "Vegetable fried rice",
                "ingredients": {"rice", "carrot", "peas", "onion", "beans"},
                "instructions": "Cook rice, lightly cook available vegetables, then mix together."
            },
            {
                "name": "Tomato vegetable pasta",
                "ingredients": {"tomato", "pasta", "onion", "capsicum"},
                "instructions": "Cook pasta and prepare a simple tomato and vegetable sauce."
            },
            {
                "name": "Fruit bowl",
                "ingredients": {"apple", "banana", "orange", "grapes", "papaya"},
                "instructions": "Wash, cut, and combine available fruits."
            },
            {
                "name": "Potato vegetable curry",
                "ingredients": {"potato", "tomato", "onion", "peas"},
                "instructions": "Cook the vegetables with suitable spices until tender."
            },
            {
                "name": "Simple lentil rice",
                "ingredients": {"rice", "dal", "lentils", "onion", "tomato"},
                "instructions": "Cook rice and lentils separately or together with suitable seasoning."
            },
            {
                "name": "Banana smoothie",
                "ingredients": {"banana", "milk", "yogurt"},
                "instructions": "Blend banana with milk or yogurt. Keep chilled and serve fresh."
            }
        ]

        matches = []
        for recipe in recipe_ideas:
            matched = [
                food for food in available_foods
                if any(key in food.lower() for key in recipe["ingredients"])
            ]
            if matched:
                matches.append((recipe, matched))

        if matches:
            st.success(f"Found {len(matches)} meal idea(s) using your inventory.")
            for recipe, matched in matches:
                with st.expander(f"🍽️ {recipe['name']}"):
                    st.write("**Ingredients found in your inventory:** " + ", ".join(matched))
                    st.write("**Simple idea:** " + recipe["instructions"])
        else:
            st.warning(
                "No recipe matches yet. Try adding common ingredients such as "
                "rice, tomato, potato, onion, banana, milk, or apple."
            )

        st.caption(
            "These are suggestions, not personalized dietary advice. "
            "Check ingredients, allergies, and food safety before preparing meals."
        )

# ------------------------- Waste Log -------------------------

elif page == "Waste Log":
    st.title("🗑️ Food Waste Log")
    st.write("Record food that was discarded to understand where waste happens.")

    with st.form("waste_form", clear_on_submit=True):
        col1, col2 = st.columns(2)
        wasted_food = col1.text_input("Food wasted", placeholder="Example: Bread")
        wasted_quantity = col2.number_input(
            "Quantity wasted", min_value=0.01, value=0.5, step=0.5
        )
        col3, col4 = st.columns(2)
        wasted_unit = col3.selectbox(
            "Unit", ["kg", "g", "litre", "ml", "pieces", "packets"],
            key="waste_unit"
        )
        reason = col4.selectbox(
            "Reason",
            ["Expired", "Too much prepared", "Spoiled", "Leftovers",
             "Damaged packaging", "Other"]
        )
        waste_date = st.date_input("Date", value=date.today())
        save_waste = st.form_submit_button("Save waste record")

        if save_waste:
            if not wasted_food.strip():
                st.error("Please enter the food name.")
            else:
                new_waste = {
                    "date": waste_date,
                    "food": wasted_food.strip(),
                    "quantity": wasted_quantity,
                    "unit": wasted_unit,
                    "reason": reason
                }
                waste = pd.concat(
                    [waste, pd.DataFrame([new_waste])],
                    ignore_index=True
                )
                save_data(waste, WASTE_FILE)
                st.success("Waste record saved.")
                st.rerun()

    st.subheader("Waste records")
    if waste.empty:
        st.info("No waste records yet.")
    else:
        st.dataframe(waste, use_container_width=True, hide_index=True)

        numeric_waste = pd.to_numeric(waste["quantity"], errors="coerce").fillna(0)
        st.metric("Total recorded quantity", f"{numeric_waste.sum():g}")
        reason_counts = waste["reason"].value_counts()
        st.subheader("Main reasons for waste")
        st.bar_chart(reason_counts)

        # Simple illustrative estimate. It assumes 2.5 kg CO2e per kg of food.
        # It is only a classroom demonstration and not a precise footprint.
        kg_rows = waste[waste["unit"].astype(str).str.lower().eq("kg")]
        kg_total = pd.to_numeric(kg_rows["quantity"], errors="coerce").fillna(0).sum()
        estimated_impact = kg_total * 2.5
        st.metric(
            "Illustrative emissions associated with logged kg",
            f"{estimated_impact:.2f} kg CO₂e",
            help="Demo assumption: 2.5 kg CO₂e per kg of discarded food. Actual impact varies by food type."
        )
        st.caption(
            "This environmental estimate is simplified for an academic demonstration. "
            "It is not a verified measurement."
        )

# ------------------------- About Project -------------------------

elif page == "About Project":
    st.title("📖About Smart Food Waste & Menu Tracker")
    st.write(
        "The Smart Food Waste & Menu Tracker is a student project designed to demonstrate how a simple "
        "digital system can help households, canteens, and small food businesses "
        "monitor food stocks and reduce avoidable food waste."
    )

    st.subheader("Problem statement")
    st.write(
        "Food may be wasted when people forget what they have, overlook expiry "
        "dates, prepare too much, or do not plan meals around available ingredients."
    )

    st.subheader("Objectives")
    st.markdown(
        """
        - Maintain a digital record of available food.
        - Highlight items that are close to their expiry dates.
        - Suggest simple meals using available ingredients.
        - Record the quantity and reasons for food waste.
        - Display basic charts to help users understand waste patterns.
        """
    )

    st.subheader("Technology used")
    st.markdown(
        """
        - **Python:** main programming language.
        - **Streamlit:** interactive web application.
        - **Pandas:** data handling and analysis.
        - **CSV files:** simple local data storage.
        """
    )

    st.subheader("Future improvements")
    st.markdown(
        """
        - Add user login and separate inventories.
        - Add barcode scanning for faster item entry.
        - Use a verified food database for more accurate expiry guidance.
        - Add more regional recipes and ingredient matching.
        - Connect to a properly validated environmental-impact dataset.
        """
    )

    st.info(
        "Data is saved locally in the 'ecoplate_data' folder beside this Python file. "
        "Keep that folder if you want to preserve your records."
    )

st.sidebar.divider()
st.sidebar.caption("EcoPlate AI | Student IDT Project")
