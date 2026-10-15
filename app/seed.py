import sys
import random
import argparse
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from app.core.database import SessionLocal, Base, engine
from app.core.security import hash_password
from app.core.logging import logger
from app.models.admin_user import AdminUser
from app.models.category import Category
from app.models.product import Product
from app.models.order import Order, OrderItem
from app.utils.formatters import slugify, generate_order_number


# Seed Categories
CATEGORIES_DATA = [
    {
        "name": "Sparklers & Flower Pots",
        "slug": "sparklers-flower-pots",
        "description": "Sparkling handhelds, colour electric sparklers, giant 50cm sparklers and fountain flower pots.",
        "image_url": "https://images.unsplash.com/photo-1533227268428-f9ed0900fb3b?w=600&auto=format&fit=crop&q=80",
        "prefix": "SPK"
    },
    {
        "name": "Ground Chakkars & Spinners",
        "slug": "ground-chakkars",
        "description": "Whirling ground spinners, deluxe zamin chakkars, and multi-colour rotating fireworks.",
        "image_url": "https://images.unsplash.com/photo-1514565131-fce0801e5785?w=600&auto=format&fit=crop&q=80",
        "prefix": "CHK"
    },
    {
        "name": "Sound Crackers & Bombs",
        "slug": "sound-crackers",
        "description": "Traditional atom bombs, hydro bombs, 2-sound crackers, bullet bombs, and thunder kings.",
        "image_url": "https://images.unsplash.com/photo-1576400883215-7083980b6197?w=600&auto=format&fit=crop&q=80",
        "prefix": "BMB"
    },
    {
        "name": "Garlands & Wala",
        "slug": "garlands-wala",
        "description": "Celebratory red crackers garlands from 100 wala up to 10,000 wala grand festival rolls.",
        "image_url": "https://images.unsplash.com/photo-1563245372-f21724e3856d?w=600&auto=format&fit=crop&q=80",
        "prefix": "GAR"
    },
    {
        "name": "Aerial & Fancy Sky Shots",
        "slug": "aerial-shots",
        "description": "Spectacular single and double sky-burst shells illuminating night skies in vivid hues.",
        "image_url": "https://images.unsplash.com/photo-1498931299472-f7a63a5a1cfa?w=600&auto=format&fit=crop&q=80",
        "prefix": "ARS"
    },
    {
        "name": "Multi-Shot Sky Symphony Cakes",
        "slug": "multi-shots",
        "description": "Synchronized multi-shot repeating cakes from 12 shots up to 240 shots grand display.",
        "image_url": "https://images.unsplash.com/photo-1513151233558-d860c5398176?w=600&auto=format&fit=crop&q=80",
        "prefix": "MLS"
    },
    {
        "name": "Rockets & Missiles",
        "slug": "rockets",
        "description": "High-altitude whistling rockets, parachute flares, and multi-break projectile rockets.",
        "image_url": "https://images.unsplash.com/photo-1531306728370-e2ebd9d7bb99?w=600&auto=format&fit=crop&q=80",
        "prefix": "RCK"
    },
    {
        "name": "Kids Special & Novelties",
        "slug": "kids-specials",
        "description": "Safe, smoke-free novelties, roll caps, serpent eggs, magic pencils, and pop-pops.",
        "image_url": "https://images.unsplash.com/photo-1509198397868-475647b2a1e5?w=600&auto=format&fit=crop&q=80",
        "prefix": "KID"
    },
    {
        "name": "Gift Boxes & Family Combos",
        "slug": "gift-boxes",
        "description": "Curated premium festival assortments packed in deluxe gifting cases for family celebrations.",
        "image_url": "https://images.unsplash.com/photo-1549465220-1a8b9238cd48?w=600&auto=format&fit=crop&q=80",
        "prefix": "GFT"
    },
    {
        "name": "Eco-Friendly Green Crackers",
        "slug": "green-crackers",
        "description": "CSIR-NEERI certified green crackers with 30% reduced emissions and sulfur-free smoke.",
        "image_url": "https://images.unsplash.com/photo-1514565131-fce0801e5785?w=600&auto=format&fit=crop&q=80",
        "prefix": "GRN"
    }
]

# Vocabulary generator for Sivakasi products
ADJECTIVES = [
    "Royal", "Deluxe", "Classic", "Imperial", "Grand", "Super", "Golden", "Silver", "Electric",
    "Sparkling", "Ultra", "Thunder", "Peacock", "Diamond", "Magic", "Twinkling", "Cosmic",
    "Starlight", "Vibrant", "Supreme", "Maharaja", "Carnival", "Spectacle", "Celestial", "Rainbow"
]

NOUNS = {
    "SPK": ["Gold Sparklers", "Colour Sparklers", "Crackling Sparklers", "Green Sparklers", "Flower Pots Special", "Ashoka Pots", "Colour Koti Fountain", "Giant Tree Fountain"],
    "CHK": ["Zamin Chakkar Special", "Deluxe Rotating Wheel", "Colour Chakkar", "Speed Wheel Spinner", "Whistling Chakkar", "Disco Chakkar"],
    "BMB": ["Hydro Bomb", "Atom Bomb", "Thunder King", "2-Sound Cracker", "Classic Bullet Bomb", "King Kong Bomb", "Mega Blast Sounder"],
    "GAR": ["100 Wala Garland", "28 Chorsa Wala", "1000 Wala Deluxe", "2000 Wala Grand Gala", "5000 Wala Giant Lari", "10000 Wala Royal Gala"],
    "ARS": ["Sky Shot Single Break", "Double Ball Sky Shell", "Night Queen Aerial", "Golden Willow Sky Blast", "7-Colour Comet Shower"],
    "MLS": ["12 Shots Sky Bloom", "25 Shots Glittering Rain", "30 Shots Royal Symphony", "60 Shots Night Wonder", "120 Shots VIP Symphony Cake", "240 Shots Grand Finale"],
    "RCK": ["Whistling Rocket", "Lunik Sky Rocket", "Parachute Flare Rocket", "Colour Smoke Rocket", "Thunderbolt Rocket"],
    "KID": ["Magic Butterfly", "Pop Pop Snapper", "Peacock Feather Spark", "Cartoon Roll Caps", "Serpent Eggs", "Magic Whip"],
    "GFT": ["Family Festive Hamper", "Mega Sivakasi Treasure Box", "VIP Deluxe Assortment", "Diwali Golden Gift Pack", "Super Saver Combo"],
    "GRN": ["Eco SWAS Green Pot", "Eco STAR Sounder", "SAFAL Low-Smoke Sparkler", "Clean Air Sky Shell", "Green Thunder Cracker"]
}


def seed_database(target_product_count: int = 3000):
    logger.info("Initializing database tables...")
    Base.metadata.create_all(bind=engine)
    db: Session = SessionLocal()

    try:
        # 1. Seed Admin User
        admin = db.query(AdminUser).filter(AdminUser.username == "admin").first()
        if not admin:
            logger.info("Creating default Super Admin user (admin / admin123)...")
            admin = AdminUser(
                username="admin",
                email="admin@sivakasicrackers.com",
                password_hash=hash_password("admin123"),
                is_active=True
            )
            db.add(admin)
            db.commit()
            logger.info("Default Admin User created successfully!")
        else:
            logger.info("Admin user already exists.")

        # 2. Seed Categories
        logger.info("Seeding Categories...")
        category_map = {}
        for cat_data in CATEGORIES_DATA:
            prefix = cat_data["prefix"]
            clean_cat_data = {k: v for k, v in cat_data.items() if k != "prefix"}
            cat = db.query(Category).filter(Category.slug == clean_cat_data["slug"]).first()
            if not cat:
                cat = Category(**clean_cat_data)
                db.add(cat)
                db.commit()
                db.refresh(cat)
            category_map[prefix] = cat
        logger.info(f"Verified {len(category_map)} categories.")

        # 3. Check existing products count
        current_count = db.query(Product).count()
        needed = target_product_count - current_count

        if needed <= 0:
            logger.info(f"Database already contains {current_count} products (target: {target_product_count}).")
        else:
            logger.info(f"Generating {needed} realistic products to reach {target_product_count} total catalog size...")
            
            prefixes = list(category_map.keys())
            batch = []
            used_slugs = set(r[0] for r in db.query(Product.slug).all())
            used_codes = set(r[0] for r in db.query(Product.product_code).all())

            for i in range(1, needed + 1):
                prefix = random.choice(prefixes)
                category = category_map[prefix]
                
                # Compose realistic product name
                adj = random.choice(ADJECTIVES)
                noun = random.choice(NOUNS[prefix])
                variant = random.choice(["", f"({random.choice(['10 Pcs', '5 Pcs', '1 Box', '1 Set', 'Giant'])})", f"Grade-{random.choice(['A', 'Special', 'Supreme'])}"])
                
                name_parts = [adj, noun]
                if variant:
                    name_parts.append(variant)
                product_name = " ".join(name_parts)

                # Generate unique product code
                code_num = 1000 + current_count + i
                product_code = f"{prefix}-{code_num}"
                while product_code in used_codes:
                    code_num += 1
                    product_code = f"{prefix}-{code_num}"
                used_codes.add(product_code)

                # Generate unique slug
                base_slug = slugify(f"{product_name}-{product_code}")
                slug = base_slug
                slug_idx = 1
                while slug in used_slugs:
                    slug = f"{base_slug}-{slug_idx}"
                    slug_idx += 1
                used_slugs.add(slug)

                # Pricing logic by category
                if prefix in ["MLS", "GFT"]:
                    orig_price = round(random.uniform(900.0, 7500.0), 2)
                    discount = random.choice([25, 30, 40, 50, 60, 65])
                elif prefix in ["ARS", "GAR"]:
                    orig_price = round(random.uniform(250.0, 3200.0), 2)
                    discount = random.choice([20, 35, 45, 55, 70])
                else:
                    orig_price = round(random.uniform(60.0, 650.0), 2)
                    discount = random.choice([15, 25, 30, 40, 50, 60])

                sell_price = round(orig_price * (1.0 - (discount / 100.0)), 2)
                stock_qty = random.randint(15, 600)
                is_featured = (random.random() < 0.12)  # 12% featured

                units = {
                    "SPK": "Box (10 Pcs)",
                    "CHK": "Box (10 Pcs)",
                    "BMB": "Box (10 Pcs)",
                    "GAR": "Pack (1 Roll)",
                    "ARS": "Box (1 Piece)",
                    "MLS": "Deluxe Cake Box",
                    "RCK": "Box (10 Pcs)",
                    "KID": "Box (1 Pack)",
                    "GFT": "Gift Hamper Case",
                    "GRN": "Certified Box"
                }

                prod = Product(
                    product_code=product_code,
                    name=product_name,
                    slug=slug,
                    category_id=category.id,
                    description=(
                        f"Original Sivakasi handcrafted fireworks. Premium chemical formulation with {discount}% festive discount. "
                        f"Complies with Indian fireworks safety standards. Ideal for vibrant Diwali family celebrations."
                    ),
                    image_url=category.image_url,
                    original_price=orig_price,
                    selling_price=sell_price,
                    discount_percentage=discount,
                    stock_quantity=stock_qty,
                    unit=units.get(prefix, "Box"),
                    is_featured=is_featured,
                    is_active=True
                )
                batch.append(prod)

                # Batch insertion for speed
                if len(batch) >= 500:
                    db.bulk_save_objects(batch)
                    db.commit()
                    logger.info(f"Inserted batch: {i}/{needed} products committed...")
                    batch = []

            if batch:
                db.bulk_save_objects(batch)
                db.commit()

            total_now = db.query(Product).count()
            logger.info(f"SUCCESS! Total catalog size is now {total_now} products.")

        # 4. Seed sample orders if none exist
        existing_orders = db.query(Order).count()
        if existing_orders == 0:
            logger.info("Seeding initial realistic orders for analytics...")
            sample_customers = [
                ("Vishwa Natarajan", "9842104521", "vishwa@example.com", "42 Kamaraj Road", "Sivakasi", "Tamil Nadu", "626123"),
                ("Rajesh Kumar", "9884012345", "rajesh@example.com", "15 Anna Salai", "Chennai", "Tamil Nadu", "600002"),
                ("Priya Sharma", "9945112233", "priya@example.com", "88 MG Road", "Bengaluru", "Karnataka", "560001"),
                ("Anand Verma", "9820011224", "anand@example.com", "204 Bandra West", "Mumbai", "Maharashtra", "400050"),
                ("Karthik Sundaram", "9789012344", "karthik@example.com", "12 Cross Cut Rd", "Coimbatore", "Tamil Nadu", "641012"),
            ]
            prods = db.query(Product).filter(Product.is_active.is_(True)).limit(15).all()

            for name, phone, email, addr, city, state, pin in sample_customers:
                order_items_data = []
                subtotal = 0.0
                selected_prods = random.sample(prods, k=random.randint(2, 4))
                
                for p in selected_prods:
                    qty = random.randint(1, 3)
                    price = float(p.selling_price)
                    item_tot = round(price * qty, 2)
                    subtotal += item_tot
                    order_items_data.append(
                        OrderItem(
                            product_id=p.id,
                            product_name_snapshot=p.name,
                            quantity=qty,
                            unit_price=price,
                            total_price=item_tot
                        )
                    )

                delivery = 200.0 if subtotal < 3000 else 500.0
                total_amt = round(subtotal + delivery, 2)
                order_num = generate_order_number()

                order = Order(
                    order_number=order_num,
                    customer_name=name,
                    customer_phone=phone,
                    customer_email=email,
                    address=addr,
                    city=city,
                    state=state,
                    pincode=pin,
                    subtotal=subtotal,
                    discount=0.0,
                    delivery_charge=delivery,
                    total_amount=total_amt,
                    payment_method="Cash on Delivery",
                    payment_status="Completed",
                    order_status=random.choice(["Delivered", "Processing", "Confirmed", "Pending"]),
                    items=order_items_data
                )
                db.add(order)

            db.commit()
            logger.info("Sample orders successfully seeded.")

    finally:
        db.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Seed Sivakasi Fireworks Database")
    parser.add_argument("--count", type=int, default=3000, help="Target total products count (default: 3000)")
    args = parser.parse_args()
    seed_database(target_product_count=args.count)
