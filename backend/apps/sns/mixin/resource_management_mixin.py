"""
Resource and state management mixin.
Includes resource management for life, energy, money, experience, etc.
"""
import logging
import json
from typing import List, Dict, Optional
from db.DBFactory import update_AiChatCfg_map

logger = logging.getLogger(__name__)


class ResourceManagementMixin:
    """Resource and state management related utilities."""

    def load_all_user_data(self):
        """Load all user data from the database."""
        try:
            # Load location info
            self.current_place = self.aichatcfg_record.current_place or ""
            self.current_position = self.aichatcfg_record.current_position or []
            self.last_position = self.aichatcfg_record.last_position or []


            logger.info("User data loaded successfully")

        except Exception as e:
            logger.error(f"Failed to load user data: {e}")

    def save_all_user_data(self):
        """Save all user data to the database."""
        try:
            update_data = {
                "current_place": self.current_place,
                "current_position": json.dumps(self.current_position, ensure_ascii=False),
                "last_position": json.dumps(self.last_position, ensure_ascii=False),
                "life_point": self.aichatcfg_record.life_point,
                "energy_point": self.aichatcfg_record.energy_point,
                "move_point": self.aichatcfg_record.move_point,
                "exp_point": self.aichatcfg_record.exp_point,
                "iq_point": self.aichatcfg_record.iq_point,
                "money": self.aichatcfg_record.money,
                "credit": self.aichatcfg_record.credit,
                "level": self.aichatcfg_record.level
            }

            update_AiChatCfg_map(**update_data)
            logger.info("User data saved successfully")

        except Exception as e:
            logger.error(f"Failed to save user data: {e}")

    def decline_life(self):
        """Decrease life points."""
        try:
            life_point = float(self.aichatcfg_record.life_point or 0)
            self.aichatcfg_record.life_point = max(0, life_point - 10)


            logger.info(f"Life point decreased to {self.aichatcfg_record.life_point}")

            # Check whether to trigger low-life event
            if float(self.aichatcfg_record.life_point or 0) <= 20:
                logger.warning("Life point is critically low!")
                # Related events can be triggered here

        except Exception as e:
            logger.error(f"Failed to decline life: {e}")

    def increase_life(self, amount=10):
        """Increase life points."""
        try:
            life_point = float(self.aichatcfg_record.life_point or 0)
            self.aichatcfg_record.life_point = min(100, life_point + amount)


            logger.info(f"Life point increased to {self.aichatcfg_record.life_point}")

        except Exception as e:
            logger.error(f"Failed to increase life: {e}")

    def decline_energy(self):
        """Decrease energy points."""
        try:
            energy_point = float(self.aichatcfg_record.energy_point or 0)
            self.aichatcfg_record.energy_point = max(0, energy_point - 10)


            logger.info(f"Energy point decreased to {self.aichatcfg_record.energy_point}")

            # Check whether to trigger low-energy event
            if float(self.aichatcfg_record.energy_point or 0) <= 20:
                logger.warning("Energy point is critically low!")

        except Exception as e:
            logger.error(f"Failed to decline energy: {e}")

    def increase_energy(self, amount=10):
        """Increase energy points."""
        try:
            energy_point = float(self.aichatcfg_record.energy_point or 0)
            self.aichatcfg_record.energy_point = min(100, energy_point + amount)


            logger.info(f"Energy point increased to {self.aichatcfg_record.energy_point}")

        except Exception as e:
            logger.error(f"Failed to increase energy: {e}")

    def decline_move_point(self, amount=5):
        """Decrease move points."""
        try:
            move_point = float(self.aichatcfg_record.move_point or 0)
            self.aichatcfg_record.move_point = max(0, move_point - amount)


            logger.info(f"Move point decreased to {self.aichatcfg_record.move_point}")

        except Exception as e:
            logger.error(f"Failed to decline move point: {e}")

    def increase_move_point(self, amount=5):
        """Increase move points."""
        try:
            move_point = float(self.aichatcfg_record.move_point or 0)
            self.aichatcfg_record.move_point = min(100, move_point + amount)


            logger.info(f"Move point increased to {self.aichatcfg_record.move_point}")

        except Exception as e:
            logger.error(f"Failed to increase move point: {e}")

    def add_money(self, amount):
        """Add money."""
        try:
            money = float(self.aichatcfg_record.money or 0) + amount
            self.aichatcfg_record.money = money

            logger.info(f"Money increased by {amount} to {money}")
            return {"status": "success", "new_balance": money}

        except Exception as e:
            logger.error(f"Failed to add money: {e}")
            return {"status": "error", "message": str(e)}

    def spend_money(self, amount):
        """Spend money."""
        try:
            money = float(self.aichatcfg_record.money or 0)
            if money < amount:
                logger.warning(f"Insufficient funds. Required: {amount}, Available: {money}")
                return {"status": "error", "message": "Insufficient funds"}

            money = money - amount
            self.aichatcfg_record.money = money

            logger.info(f"Money decreased by {amount} to {money}")
            return {"status": "success", "new_balance": money}

        except Exception as e:
            logger.error(f"Failed to spend money: {e}")
            return {"status": "error", "message": str(e)}

    def add_exp(self, amount):
        """Add experience points."""
        try:
            exp_point = float(self.aichatcfg_record.exp_point or 0) + amount
            self.aichatcfg_record.exp_point = exp_point

            # Check whether to level up
            level = int(self.aichatcfg_record.level or 1)
            level_up_threshold = level * 100
            if exp_point >= level_up_threshold:
                self.level_up()


            logger.info(f"Experience increased by {amount} to {self.aichatcfg_record.exp_point}")

        except Exception as e:
            logger.error(f"Failed to add experience: {e}")

    def level_up(self):
        """Level up."""
        try:
            level = int(self.aichatcfg_record.level or 1) + 1
            self.aichatcfg_record.level = level

            # Level-up rewards
            self.aichatcfg_record.life_point = 100
            self.aichatcfg_record.energy_point = 100
            self.aichatcfg_record.move_point = 100
            iq_point = float(self.aichatcfg_record.iq_point or 0)
            self.aichatcfg_record.iq_point = min(100, iq_point + 5)

            logger.info(f"Level up! New level: {level}")

        except Exception as e:
            logger.error(f"Failed to level up: {e}")

    def get_resource_status(self):
        """Get current resource status."""
        return {
            "life_point": self.aichatcfg_record.life_point,
            "energy_point": self.aichatcfg_record.energy_point,
            "move_point": self.aichatcfg_record.move_point,
            "exp_point": self.aichatcfg_record.exp_point,
            "iq_point": self.aichatcfg_record.iq_point,
            "money": self.aichatcfg_record.money,
            "credit": self.aichatcfg_record.credit,
            "level": self.aichatcfg_record.level
        }

    def format_resource_display(self):
        """Format resource display."""
        return f"""
* Funds: {float(self.aichatcfg_record.money or 0):.2f} CNY
* Health: {self.aichatcfg_record.life_point}%
* Energy: {self.aichatcfg_record.energy_point}%
* Action points: {self.aichatcfg_record.move_point}%
* Experience: {self.aichatcfg_record.exp_point}
* Intelligence: {self.aichatcfg_record.iq_point}
* Credit: {self.aichatcfg_record.credit}
* Level: {self.aichatcfg_record.level}
        """.strip()
