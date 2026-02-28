#!/usr/bin/env python3
"""
Echoes of Aetherfall: Sovereign Edition
---------------------------------------
A long-form premium terminal RPG + trade sim designed for ~10h runs.

Highlights:
- Story campaign with chapter bosses and branching contracts.
- Dynamic regional market and caravan cargo system (money-focused gameplay).
- Persistent saves with 3 slots + run statistics.
- Scalable combat with abilities, stamina management, and tactical actions.
"""

from __future__ import annotations

import json
import random
import textwrap
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple

SAVE_DIR = Path("saves")
SAVE_VERSION = 2
LINE_WIDTH = 92


GOODS = {
    "Aether Silk": {"base": 55, "volatility": 0.25},
    "Star Iron": {"base": 90, "volatility": 0.35},
    "Moon Herbs": {"base": 30, "volatility": 0.2},
    "Sunglass": {"base": 72, "volatility": 0.3},
}

REGIONS = {
    "Skyrest": {"economy": (0.95, 1.15), "danger": 1},
    "Verdant Reach": {"economy": (0.85, 1.25), "danger": 2},
    "Ashen Wastes": {"economy": (0.75, 1.35), "danger": 3},
    "Frostvein": {"economy": (0.7, 1.4), "danger": 4},
    "Umbral Sea": {"economy": (0.65, 1.5), "danger": 5},
}

ENEMY_TABLE = {
    1: [("Bandit Collector", 58, 11, 4, 26), ("Ridge Wolf", 46, 10, 3, 18)],
    2: [("Mire Stalker", 80, 14, 7, 45), ("Bog Goliath", 88, 13, 8, 48)],
    3: [("Ash Vanguard", 105, 18, 10, 62), ("Magma Coil", 120, 19, 9, 70)],
    4: [("Frost Revenant", 148, 21, 13, 95), ("Shard Roc", 160, 22, 12, 108)],
    5: [("Void Corsair", 188, 26, 16, 145), ("Abyss Hydra", 225, 30, 17, 180)],
}

CHAPTER_TITLES = {
    1: "The Violet Fracture",
    2: "Roots Below the Empire",
    3: "The Cinder Throne",
    4: "Chorale of Frozen Glass",
    5: "Night Tide Sovereign",
    6: "Echoes of Aetherfall",
}


def wrap(text: str) -> str:
    return "\n".join(textwrap.wrap(text, width=LINE_WIDTH))


def ask_int(prompt: str, minimum: int, maximum: int) -> int:
    while True:
        raw = input(prompt).strip()
        if not raw.isdigit():
            print("Please enter a valid number.")
            continue
        value = int(raw)
        if minimum <= value <= maximum:
            return value
        print(f"Please enter a number between {minimum} and {maximum}.")


@dataclass
class Player:
    name: str
    title: str = "Wanderer"
    hp: int = 130
    max_hp: int = 130
    stamina: int = 70
    max_stamina: int = 70
    attack: int = 16
    defense: int = 9
    level: int = 1
    xp: int = 0
    gold: int = 120
    day: int = 1
    location: str = "Skyrest"
    chapter: int = 1
    relics: int = 0
    renown: int = 0
    potions: int = 3
    elixirs: int = 1
    ore: int = 0
    herbs: int = 0
    cargo_capacity: int = 16
    cargo: Dict[str, int] = field(default_factory=dict)
    contracts_completed: int = 0
    bosses_defeated: int = 0
    total_profit: int = 0


class Game:
    def __init__(self, rng_seed: Optional[int] = None) -> None:
        self.rng = random.Random(rng_seed)
        self.player: Optional[Player] = None
        self.game_over = False
        self.market_state = self.build_market_state()

    def build_market_state(self) -> Dict[str, Dict[str, int]]:
        state: Dict[str, Dict[str, int]] = {}
        for region, meta in REGIONS.items():
            low, high = meta["economy"]
            prices: Dict[str, int] = {}
            for good, cfg in GOODS.items():
                drift = self.rng.uniform(low, high)
                vol = self.rng.uniform(1 - cfg["volatility"], 1 + cfg["volatility"])
                prices[good] = max(8, int(cfg["base"] * drift * vol))
            state[region] = prices
        return state

    def daily_market_shift(self) -> None:
        for region, goods in self.market_state.items():
            low, high = REGIONS[region]["economy"]
            for good, price in goods.items():
                cfg = GOODS[good]
                movement = self.rng.uniform(0.92, 1.08) * self.rng.uniform(low, high)
                cap_low = int(cfg["base"] * 0.45)
                cap_high = int(cfg["base"] * 2.3)
                goods[good] = max(cap_low, min(cap_high, int(price * movement)))

    def main_menu(self) -> None:
        while True:
            print("\n=== ECHOES OF AETHERFALL: SOVEREIGN EDITION ===")
            print("1) New Game")
            print("2) Load Game")
            print("3) Quit")
            choice = ask_int("Choose: ", 1, 3)
            if choice == 1:
                self.new_game()
                self.game_loop()
            elif choice == 2:
                if self.load_game():
                    self.game_loop()
            else:
                print("May fortune guide your ventures.")
                return

    def new_game(self) -> None:
        print(wrap(
            "Seventy nights of violet storms have split the sky. The Imperial Treasury offers a "
            "fortune to whoever can end the rift crisis, and any merchant house you build along the "
            "way will be yours to command."
        ))
        name = input("Enter your sovereign's name: ").strip() or "Arin"
        self.player = Player(name=name)
        self.market_state = self.build_market_state()
        self.game_over = False
        print(wrap(
            f"Welcome, {name}. This is a long-form campaign tuned for around 10 hours if you play "
            "story and trade seriously. Save often."
        ))

    def save_game(self) -> None:
        if not self.player:
            return
        SAVE_DIR.mkdir(exist_ok=True)
        slot = ask_int("Save slot (1-3): ", 1, 3)
        path = SAVE_DIR / f"slot_{slot}.json"
        payload = {
            "version": SAVE_VERSION,
            "player": asdict(self.player),
            "market_state": self.market_state,
        }
        path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        print(f"Saved to {path}.")

    def load_game(self) -> bool:
        SAVE_DIR.mkdir(exist_ok=True)
        available = sorted(SAVE_DIR.glob("slot_*.json"))
        if not available:
            print("No save files found.")
            return False
        print("Available saves:")
        for p in available:
            print(f"- {p.name}")
        slot = ask_int("Load slot (1-3): ", 1, 3)
        path = SAVE_DIR / f"slot_{slot}.json"
        if not path.exists():
            print("Slot is empty.")
            return False
        data = json.loads(path.read_text(encoding="utf-8"))
        if data.get("version") != SAVE_VERSION:
            print("Save version mismatch. Start a new run for this version.")
            return False
        self.player = Player(**data["player"])
        self.market_state = data.get("market_state") or self.build_market_state()
        self.game_over = False
        print(f"Loaded {self.player.name} from {path}.")
        return True

    def game_loop(self) -> None:
        assert self.player is not None
        while not self.game_over:
            p = self.player
            self.check_progression()
            self.render_hud()
            print("1) Travel")
            print("2) Story Quest")
            print("3) Hunt Contracts")
            print("4) Trade Market")
            print("5) Rest / Recover")
            print("6) Inventory")
            print("7) Craft & Upgrades")
            print("8) Save")
            print("9) Quit to Main Menu")
            choice = ask_int("Action: ", 1, 9)
            if choice == 1:
                self.travel()
            elif choice == 2:
                self.story_quest()
            elif choice == 3:
                self.contracts()
            elif choice == 4:
                self.trade_menu()
            elif choice == 5:
                self.rest()
            elif choice == 6:
                self.inventory()
            elif choice == 7:
                self.craft()
            elif choice == 8:
                self.save_game()
            else:
                print("Returning to main menu...")
                return

    def render_hud(self) -> None:
        assert self.player is not None
        p = self.player
        cargo_used = sum(p.cargo.values())
        print(f"\n--- Day {p.day} | {p.name} the {p.title} | Lv{p.level} ---")
        print(
            f"{p.location} | HP {p.hp}/{p.max_hp} | STA {p.stamina}/{p.max_stamina} | "
            f"ATK {p.attack} DEF {p.defense}"
        )
        print(
            f"Gold {p.gold} | Profit {p.total_profit} | Relics {p.relics}/5 | Chapter {p.chapter}: "
            f"{CHAPTER_TITLES.get(p.chapter, 'Finale')}"
        )
        print(f"Cargo {cargo_used}/{p.cargo_capacity} | Contracts {p.contracts_completed} | Renown {p.renown}")

    def travel(self) -> None:
        assert self.player is not None
        p = self.player
        places = list(REGIONS.keys())
        for i, place in enumerate(places, start=1):
            print(f"{i}) {place}")
        idx = ask_int("Travel to: ", 1, len(places)) - 1
        destination = places[idx]
        if destination == p.location:
            print("You are already here.")
            return
        p.location = destination
        p.day += 1
        p.stamina = max(6, p.stamina - 10)
        self.daily_market_shift()
        print(wrap(f"Your caravan reaches {destination}. Prices shift as rumors spread through the market."))
        self.random_event()

    def story_quest(self) -> None:
        assert self.player is not None
        p = self.player
        chapter = min(p.chapter, 5)
        encounters = 2 if chapter < 4 else 3
        print(wrap("You accept a high-risk story operation against forces tied to the sky-rift."))

        bonus_gold = 0
        for _ in range(encounters):
            won, reward = self.combat(chapter, is_boss=False)
            if not won:
                return
            bonus_gold += reward

        xp_gain = 50 + chapter * 38
        renown_gain = 4 + chapter
        p.xp += xp_gain
        p.renown += renown_gain
        p.gold += bonus_gold + 45
        p.day += 1
        p.stamina = max(0, p.stamina - 16)

        if self.rng.random() < 0.55:
            p.herbs += self.rng.randint(1, 2)
        if self.rng.random() < 0.45:
            p.ore += 1

        print(wrap(f"Operation complete. +{xp_gain} XP, +{bonus_gold + 45} gold, +{renown_gain} renown."))
        self.maybe_level_up()

        if p.renown >= 14 + chapter * 8 and p.relics < chapter:
            self.boss_battle(chapter)

    def contracts(self) -> None:
        assert self.player is not None
        p = self.player
        regional_danger = REGIONS[p.location]["danger"]
        target_runs = 1 if p.chapter <= 2 else 2
        print(wrap("You post notices for paid security contracts and monster clearance bounties."))
        total = 0
        for _ in range(target_runs):
            won, reward = self.combat(max(1, regional_danger), is_boss=False)
            if not won:
                return
            total += reward

        contract_bonus = 30 + p.chapter * 10
        p.contracts_completed += 1
        p.gold += total + contract_bonus
        p.total_profit += total + contract_bonus
        p.xp += 32 + p.chapter * 12
        p.day += 1
        p.stamina = max(0, p.stamina - 12)
        if self.rng.random() < 0.35:
            p.potions += 1
            print("A grateful patron gifts you a potion.")
        print(f"Contracts fulfilled. Revenue: {total + contract_bonus} gold.")
        self.maybe_level_up()

    def cargo_space_left(self) -> int:
        assert self.player is not None
        return self.player.cargo_capacity - sum(self.player.cargo.values())

    def trade_menu(self) -> None:
        assert self.player is not None
        p = self.player
        prices = self.market_state[p.location]
        print(f"\n{p.location} Exchange")
        print("1) Buy goods")
        print("2) Sell goods")
        print("3) Expand caravan (+8 slots for 220 gold)")
        print("4) Back")
        choice = ask_int("Choice: ", 1, 4)
        if choice == 4:
            return

        goods = list(GOODS.keys())
        if choice in (1, 2):
            for i, good in enumerate(goods, 1):
                owned = p.cargo.get(good, 0)
                print(f"{i}) {good:12} price {prices[good]:>3} | you own {owned}")
            idx = ask_int("Select good: ", 1, len(goods)) - 1
            selected = goods[idx]
            price = prices[selected]
            if choice == 1:
                max_buy = min(self.cargo_space_left(), p.gold // price)
                if max_buy <= 0:
                    print("No room or not enough gold.")
                    return
                qty = ask_int(f"How many (1-{max_buy}): ", 1, max_buy)
                cost = qty * price
                p.gold -= cost
                p.cargo[selected] = p.cargo.get(selected, 0) + qty
                print(f"Bought {qty} {selected} for {cost} gold.")
            else:
                owned = p.cargo.get(selected, 0)
                if owned <= 0:
                    print("You own none of this good.")
                    return
                qty = ask_int(f"How many (1-{owned}): ", 1, owned)
                revenue = qty * price
                p.gold += revenue
                p.total_profit += revenue
                p.cargo[selected] = owned - qty
                if p.cargo[selected] == 0:
                    del p.cargo[selected]
                print(f"Sold {qty} {selected} for {revenue} gold.")
                p.renown += 1
        elif choice == 3:
            if p.gold < 220:
                print("Not enough gold.")
                return
            p.gold -= 220
            p.cargo_capacity += 8
            print("Caravan expanded! New capacity unlocked.")

    def rest(self) -> None:
        assert self.player is not None
        p = self.player
        cost = 22 + p.chapter * 4
        print(f"Recover at a premium inn for {cost} gold?")
        print("1) Yes")
        print("2) No")
        if ask_int("Choice: ", 1, 2) == 1:
            if p.gold < cost:
                print("Not enough gold.")
                return
            p.gold -= cost
            p.hp = p.max_hp
            p.stamina = p.max_stamina
            p.day += 1
            self.daily_market_shift()
            print("Fully restored.")
        else:
            print("You continue without rest.")

    def inventory(self) -> None:
        assert self.player is not None
        p = self.player
        print("\nInventory")
        print(f"Potions: {p.potions} (+70 HP)")
        print(f"Elixirs: {p.elixirs} (full stamina + 20 HP)")
        print(f"Ore: {p.ore} | Herbs: {p.herbs}")
        cargo_line = ", ".join(f"{k}:{v}" for k, v in p.cargo.items()) or "No cargo"
        print(f"Cargo: {cargo_line}")
        print("1) Use Potion")
        print("2) Use Elixir")
        print("3) Back")
        choice = ask_int("Choice: ", 1, 3)
        if choice == 1:
            if p.potions <= 0:
                print("No potions left.")
                return
            p.potions -= 1
            p.hp = min(p.max_hp, p.hp + 70)
            print("Potion used.")
        elif choice == 2:
            if p.elixirs <= 0:
                print("No elixirs left.")
                return
            p.elixirs -= 1
            p.stamina = p.max_stamina
            p.hp = min(p.max_hp, p.hp + 20)
            print("Elixir consumed.")

    def craft(self) -> None:
        assert self.player is not None
        p = self.player
        print("\nCraft & Upgrades")
        print("1) Brew potion (2 herbs -> 1 potion)")
        print("2) Refine elixir (3 herbs + 1 ore -> 1 elixir)")
        print("3) Forge edge (+2 ATK, cost: 2 ore + 110 gold)")
        print("4) Harden plate (+2 DEF, cost: 2 ore + 110 gold)")
        print("5) Back")
        ch = ask_int("Choice: ", 1, 5)
        if ch == 1:
            if p.herbs < 2:
                print("Not enough herbs.")
                return
            p.herbs -= 2
            p.potions += 1
            print("Potion brewed.")
        elif ch == 2:
            if p.herbs < 3 or p.ore < 1:
                print("Need 3 herbs and 1 ore.")
                return
            p.herbs -= 3
            p.ore -= 1
            p.elixirs += 1
            print("Elixir refined.")
        elif ch == 3:
            if p.ore < 2 or p.gold < 110:
                print("Need 2 ore and 110 gold.")
                return
            p.ore -= 2
            p.gold -= 110
            p.attack += 2
            print("Your weapon glows with a sharper rune.")
        elif ch == 4:
            if p.ore < 2 or p.gold < 110:
                print("Need 2 ore and 110 gold.")
                return
            p.ore -= 2
            p.gold -= 110
            p.defense += 2
            print("Armor reinforcement complete.")

    def random_event(self) -> None:
        assert self.player is not None
        p = self.player
        roll = self.rng.random()
        if roll < 0.23:
            reward = self.rng.randint(22, 70)
            p.gold += reward
            p.total_profit += reward
            print(f"A courier overpays for urgent escort rights. +{reward} gold.")
        elif roll < 0.4:
            gain = self.rng.randint(1, 2)
            p.herbs += gain
            print(f"You discover moon-herb terraces (+{gain}).")
        elif roll < 0.56:
            p.ore += 1
            print("An abandoned quarry yields rare ore (+1).")
        elif roll < 0.72:
            print("Roadside ambush!")
            self.combat(max(1, REGIONS[p.location]["danger"] - 1), is_boss=False)

    def combat(self, difficulty: int, is_boss: bool) -> Tuple[bool, int]:
        assert self.player is not None
        p = self.player
        enemy_name, hp, atk, defense, reward = self.generate_enemy(difficulty, is_boss)
        print(f"\nA {enemy_name} appears! (HP {hp})")

        while hp > 0 and p.hp > 0:
            print(f"\n{p.name}: HP {p.hp}/{p.max_hp} | STA {p.stamina}/{p.max_stamina}")
            print(f"{enemy_name}: HP {hp}")
            print("1) Strike (8 STA)")
            print("2) Heavy Blow (14 STA)")
            print("3) Guard (+10 STA, halve incoming)")
            print("4) Tactical Focus (12 STA, next attack +40%)")
            print("5) Use Potion")
            action = ask_int("Choose action: ", 1, 5)

            player_guard = False
            focused = False
            if action == 1:
                if p.stamina < 8:
                    print("Too exhausted. You miss the moment.")
                else:
                    p.stamina -= 8
                    dmg = max(1, p.attack + self.rng.randint(0, 8) - defense)
                    hp -= dmg
                    print(f"You strike for {dmg}.")
            elif action == 2:
                if p.stamina < 14:
                    print("Not enough stamina.")
                else:
                    p.stamina -= 14
                    dmg = max(3, p.attack + 10 + self.rng.randint(0, 12) - defense)
                    hp -= dmg
                    print(f"Heavy blow lands for {dmg}!")
            elif action == 3:
                player_guard = True
                p.stamina = min(p.max_stamina, p.stamina + 10)
                print("You brace and steady your breathing.")
            elif action == 4:
                if p.stamina < 12:
                    print("Not enough stamina.")
                else:
                    p.stamina -= 12
                    focused = True
                    dmg = max(2, int((p.attack + self.rng.randint(4, 12) - defense) * 1.4))
                    hp -= dmg
                    print(f"Focused strike deals {dmg} damage.")
            else:
                if p.potions <= 0:
                    print("No potions.")
                else:
                    p.potions -= 1
                    p.hp = min(p.max_hp, p.hp + 70)
                    print("Potion used.")

            if hp <= 0:
                break

            enemy_dmg = max(1, atk + self.rng.randint(0, 7) - p.defense)
            if is_boss and self.rng.random() < 0.2:
                enemy_dmg += 5
                print(f"{enemy_name} channels rift energy!")
            if player_guard:
                enemy_dmg = max(1, enemy_dmg // 2)
            if focused and self.rng.random() < 0.25:
                p.stamina = min(p.max_stamina, p.stamina + 5)
            p.hp -= enemy_dmg
            print(f"{enemy_name} hits you for {enemy_dmg}.")

        if p.hp <= 0:
            print("You collapse in battle...")
            self.handle_defeat()
            return False, 0

        print(f"You defeated {enemy_name}!")
        return True, reward

    def generate_enemy(self, difficulty: int, is_boss: bool) -> Tuple[str, int, int, int, int]:
        if is_boss:
            names = {
                1: "Verdant Warden",
                2: "Ember Tyrant",
                3: "Matriarch of Glass",
                4: "Leviathan Herald",
                5: "Rift Sovereign",
            }
            base_hp = 140 + difficulty * 62
            return (
                names.get(difficulty, "Ancient Monolith"),
                base_hp,
                17 + difficulty * 4,
                8 + difficulty * 3,
                180 + difficulty * 75,
            )
        return self.rng.choice(ENEMY_TABLE.get(difficulty, ENEMY_TABLE[1]))

    def boss_battle(self, chapter: int) -> None:
        assert self.player is not None
        p = self.player
        print(wrap("A chapter boss descends. Victory secures a relic shard and massive treasury rights."))
        won, reward = self.combat(chapter, is_boss=True)
        if not won:
            return
        p.relics += 1
        p.bosses_defeated += 1
        p.gold += reward
        p.total_profit += reward
        p.xp += 130 + chapter * 80
        p.renown = 0
        p.chapter = min(6, p.chapter + 1)
        p.elixirs += 1

        if p.relics >= 3:
            p.title = "Guildmaster"
        if p.relics >= 5:
            p.title = "Sovereign of the Rift"

        print(wrap("Relic claimed. Your influence spreads across every market and military council."))
        self.maybe_level_up()
        if p.relics >= 5:
            self.finale()

    def maybe_level_up(self) -> None:
        assert self.player is not None
        p = self.player
        while p.xp >= self.level_threshold(p.level):
            p.xp -= self.level_threshold(p.level)
            p.level += 1
            p.max_hp += 20
            p.max_stamina += 9
            p.attack += 3
            p.defense += 2
            p.hp = p.max_hp
            p.stamina = p.max_stamina
            print(wrap(f"Level up! You reached level {p.level}. All core stats increased."))

    @staticmethod
    def level_threshold(level: int) -> int:
        return 95 + (level - 1) * 60

    def check_progression(self) -> None:
        assert self.player is not None
        p = self.player
        if p.day % 7 == 0:
            print(wrap("Another week passes. Demand surges, roads shift, and monsters grow bolder."))
        if p.stamina <= 0:
            print("You are exhausted and need immediate recovery.")
            self.rest()

    def handle_defeat(self) -> None:
        assert self.player is not None
        p = self.player
        penalty = min(p.gold, 55 + p.chapter * 12)
        p.gold -= penalty
        p.hp = max(1, p.max_hp // 2)
        p.stamina = max(12, p.max_stamina // 2)
        p.day += 1
        self.daily_market_shift()
        print(wrap(f"A rescue convoy retrieves you. You lose {penalty} gold and one day."))

    def finale(self) -> None:
        assert self.player is not None
        p = self.player
        print("\n=== FINAL CHAPTER: ECHOES OF AETHERFALL ===")
        print(wrap("With all relics assembled, you lead a coalition fleet into the rift citadel."))
        for stage in range(1, 4):
            print(f"Final battle {stage}/3")
            won, reward = self.combat(5, is_boss=(stage >= 2))
            if not won:
                return
            p.gold += reward
            p.total_profit += reward
            p.xp += 200
            self.maybe_level_up()

        print(wrap(
            "You seal the celestial wound, inherit the imperial trade charter, and your name becomes "
            "a permanent currency-grade symbol across the continent. Campaign complete."
        ))
        self.game_over = True
        self.show_epilogue()

    def show_epilogue(self) -> None:
        assert self.player is not None
        p = self.player
        score = (
            p.gold
            + p.total_profit
            + p.level * 150
            + p.contracts_completed * 120
            + p.bosses_defeated * 400
        )
        print("\n=== EPILOGUE REPORT ===")
        print(f"Title: {p.title}")
        print(f"Final Level: {p.level}")
        print(f"Relics Secured: {p.relics}/5")
        print(f"Contracts Completed: {p.contracts_completed}")
        print(f"Total Profit Logged: {p.total_profit} gold")
        print(f"Legacy Score: {score}")


def main() -> None:
    game = Game()
    game.main_menu()


if __name__ == "__main__":
    main()
