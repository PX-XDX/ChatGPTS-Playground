
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

    d
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
