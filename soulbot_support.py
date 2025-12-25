"""Module containing support command for the main bot using SQLAlchemy ORM."""

import random
from typing import Any, Dict, List, Optional, Tuple

import arrow
from loguru import logger
from sqlalchemy import Boolean, Column, Integer, String, Text, create_engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import Session, sessionmaker

# Timezone constants
MT = arrow.now("US/Mountain").tzinfo
PT = arrow.now("US/Pacific").tzinfo
CT = arrow.now("US/Central").tzinfo
ET = arrow.now("US/Eastern").tzinfo
UTC = arrow.utcnow().tzinfo

# SQLAlchemy setup
Base = declarative_base()


class NextGame(Base):
    """Next game schedule table."""

    __tablename__ = "next_game"

    guild_id = Column(Integer, primary_key=True)
    created_date = Column(Integer, nullable=False)
    next_date = Column(Integer, nullable=False)
    announce_on = Column(Boolean, default=False, nullable=False)


class Quote(Base):
    """Quotes table."""

    __tablename__ = "quotes"

    id = Column(Integer, primary_key=True, autoincrement=True)
    guild_id = Column(Integer, nullable=False)
    quote = Column(Text, nullable=False)


class Initiative(Base):
    """Initiative tracker table."""

    __tablename__ = "initiative"

    id = Column(Integer, primary_key=True, autoincrement=True)
    guild_id = Column(Integer, nullable=False)
    name = Column(String(255), nullable=False)
    init = Column(Integer, nullable=False)


class Config(Base):
    """Guild configuration table."""

    __tablename__ = "config"

    guild_id = Column(Integer, primary_key=True)
    prefix = Column(String(10), nullable=False)
    next_game_start = Column(String(20), nullable=False)
    next_game_interval = Column(Integer, nullable=False)
    announce_channel = Column(String(255), nullable=False)


class DatabaseIO:
    """Class definition to contain all interactions with the SQLAlchemy database."""

    def __init__(self, database_url: str = "sqlite:///data/discordbot.sql"):
        """Initialize database connection and create tables."""
        self.engine = create_engine(
            database_url,
            echo=False,  # Set to True for SQL debugging
            connect_args={"check_same_thread": False} if database_url.startswith("sqlite") else {},
        )

        # Create tables
        Base.metadata.create_all(self.engine)

        # Create session factory
        self.SessionLocal = sessionmaker(bind=self.engine)
        logger.info("Database initialized with SQLAlchemy")

    def get_session(self) -> Session:
        """Get a database session."""
        return self.SessionLocal()

    def init_db_add(self, init_insert: List[Tuple[int, str, int]]) -> None:
        """Insert/overwrite Initiative tracker data into the database.

        :param init_insert: List of tuples containing (guild_id, name, init) values.
        """
        try:
            with self.get_session() as session:
                # Clear existing records for the guild
                if init_insert:
                    guild_id = init_insert[0][0]
                    session.query(Initiative).filter(Initiative.guild_id == guild_id).delete()

                # Add new records
                for guild_id, name, init_value in init_insert:
                    initiative = Initiative(guild_id=guild_id, name=name, init=init_value)
                    session.add(initiative)

                session.commit()
                logger.debug(f"Added {len(init_insert)} initiative records")
        except Exception as e:
            logger.error(f"Error adding initiative data: {e}")
            raise

    def init_db_reset(self, guild_id: int) -> None:
        """Delete initiative table data for a specific guild.

        :param guild_id: Discord guild ID.
        """
        try:
            with self.get_session() as session:
                deleted = session.query(Initiative).filter(Initiative.guild_id == guild_id).delete()
                session.commit()
                logger.debug(f"Reset initiative for guild {guild_id}, deleted {deleted} records")
        except Exception as e:
            logger.error(f"Error resetting initiative data: {e}")
            raise

    def init_db_rebuild(self, guild_id: int) -> List[Tuple[str, int]]:
        """Retrieve initiative table from the database to rebuild the bot data.

        :param guild_id: Discord guild ID.
        :return: List of tuples of all player/NPC names and initiative values.
        """
        try:
            with self.get_session() as session:
                results = session.query(Initiative.name, Initiative.init).filter(Initiative.guild_id == guild_id).all()
                logger.debug(f"Retrieved {len(results)} initiative records for guild {guild_id}")
                return results
        except Exception as e:
            logger.error(f"Error rebuilding initiative data: {e}")
            raise

    def quote_db_add(self, quote_insert: str, guild_id: int) -> None:
        """Add new quote to the database.

        :param quote_insert: Text to add to database.
        :param guild_id: Discord guild ID.
        """
        try:
            with self.get_session() as session:
                quote = Quote(guild_id=guild_id, quote=quote_insert)
                session.add(quote)
                session.commit()
                logger.debug(f"Added quote for guild {guild_id}")
        except Exception as e:
            logger.error(f"Error adding quote: {e}")
            raise

    def quote_db_search(self, quote_search: str, guild_id: int) -> str:
        """Search database for entries containing text string.

        :param quote_search: Text to search for in existing quotes.
        :param guild_id: Discord guild ID.
        :return: Return random quote, or failure message.
        """
        try:
            with self.get_session() as session:
                quotes = (
                    session.query(Quote.quote)
                    .filter(Quote.guild_id == guild_id)
                    .filter(Quote.quote.contains(quote_search))
                    .all()
                )

                if quotes:
                    random_quote = random.choice(quotes)[0]
                    logger.debug(f"Found quote containing '{quote_search}' for guild {guild_id}")
                    return f'QUOTE: "{random_quote}"'
                else:
                    logger.debug(f"No quotes found containing '{quote_search}' for guild {guild_id}")
                    return f'No quote found with the term "{quote_search}"'
        except Exception as e:
            logger.error(f"Error searching quotes: {e}")
            return f"Error searching for quotes: {e}"

    def quote_db_random(self, guild_id: int) -> str:
        """Pull random line from the database.

        :param guild_id: Discord guild ID.
        :return: Text from randomly selected database entry.
        """
        try:
            with self.get_session() as session:
                # Get random quote using ORDER BY RANDOM()
                quote = session.query(Quote.quote).filter(Quote.guild_id == guild_id).order_by("RANDOM()").first()

                if quote:
                    logger.debug(f"Retrieved random quote for guild {guild_id}")
                    return f'QUOTE: "{quote[0]}"'
                else:
                    logger.debug(f"No quotes available for guild {guild_id}")
                    return "No quotes in the database."
        except Exception as e:
            logger.error(f"Error getting random quote: {e}")
            return "No quotes in the database."

    def next_game_db_get(self, guild_id: int) -> Optional[Tuple[int, bool]]:
        """Pull Next Game date from the database.

        :param guild_id: Discord guild ID.
        :return: Tuple of (next_date, announce_on) or None.
        """
        try:
            with self.get_session() as session:
                result = (
                    session.query(NextGame.next_date, NextGame.announce_on)
                    .filter(NextGame.guild_id == guild_id)
                    .first()
                )
                logger.debug(f"Retrieved next game data for guild {guild_id}")
                return result
        except Exception as e:
            logger.error(f"Error getting next game data: {e}")
            return None

    def next_game_db_add(self, output_date: int, guild_id: int) -> None:
        """Replace current next game data with supplied new date.

        :param output_date: Unix timestamp of the next game.
        :param guild_id: Discord guild ID.
        """
        try:
            with self.get_session() as session:
                # Try to update existing record
                existing: NextGame = session.query(NextGame).filter(NextGame.guild_id == guild_id).first()

                if existing:
                    existing.next_date = output_date
                    existing.created_date = arrow.now(UTC).int_timestamp
                    existing.announce_on = False  # Reset announcements when date changes
                else:
                    # Create new record
                    next_game = NextGame(
                        guild_id=guild_id,
                        created_date=arrow.now(UTC).int_timestamp,
                        next_date=output_date,
                        announce_on=False,
                    )
                    session.add(next_game)

                session.commit()
                logger.debug(f"Updated next game date for guild {guild_id}")
        except Exception as e:
            logger.error(f"Error adding next game data: {e}")
            raise

    def next_game_announce_toggle(self, state: int, guild_id: int) -> None:
        """Toggle the announce_on for the given guild ID.

        :param state: 0 or 1 (False or True).
        :param guild_id: Discord guild ID.
        """
        try:
            with self.get_session() as session:
                next_game = session.query(NextGame).filter(NextGame.guild_id == guild_id).first()
                if next_game:
                    next_game.announce_on = bool(state)
                    session.commit()
                    logger.debug(f"Toggled announcements to {bool(state)} for guild {guild_id}")
        except Exception as e:
            logger.error(f"Error toggling announcements: {e}")
            raise

    def next_game_get_defaults(self, guild_id: int) -> Optional[Tuple[str, int]]:
        """Get the default next game start time and interval from the config database.

        :param guild_id: Discord guild ID.
        :return: Tuple of (next_game_start, next_game_interval) or None.
        """
        try:
            with self.get_session() as session:
                result = (
                    session.query(Config.next_game_start, Config.next_game_interval)
                    .filter(Config.guild_id == guild_id)
                    .first()
                )
                logger.debug(f"Retrieved next game defaults for guild {guild_id}")
                return result
        except Exception as e:
            logger.error(f"Error getting next game defaults: {e}")
            return None

    def next_game_get_all_announcing(self) -> List[Tuple[int, int]]:
        """Get all guilds that have announcements enabled.

        :return: List of tuples (guild_id, next_date).
        """
        try:
            with self.get_session() as session:
                results = session.query(NextGame.guild_id, NextGame.next_date).filter(NextGame.announce_on).all()
                logger.debug(f"Retrieved {len(results)} guilds with announcements enabled")
                return results
        except Exception as e:
            logger.error(f"Error getting announcing guilds: {e}")
            return []

    def config_all_prefix_load(self) -> Dict[int, str]:
        """Load config settings for all registered guilds.

        :return: Dictionary mapping guild_id to prefix.
        """
        try:
            with self.get_session() as session:
                results = session.query(Config.guild_id, Config.prefix).all()
                config_dict = {guild_id: prefix for guild_id, prefix in results}
                logger.debug(f"Loaded prefixes for {len(config_dict)} guilds")
                return config_dict
        except Exception as e:
            logger.error(f"Error loading all prefixes: {e}")
            return {}

    def config_insert_all(
        self,
        guild_id: int,
        prefix: str,
        default_time: str,
        default_interval: int,
        announce_channel: str,
    ) -> None:
        """Create DB row for new server with values.

        :param guild_id: Discord guild ID.
        :param prefix: Command prefix for the guild.
        :param default_time: Default game start time.
        :param default_interval: Default interval between games.
        :param announce_channel: Channel name for announcements.
        """
        try:
            with self.get_session() as session:
                config = Config(
                    guild_id=guild_id,
                    prefix=prefix,
                    next_game_start=default_time,
                    next_game_interval=default_interval,
                    announce_channel=announce_channel,
                )
                session.add(config)
                session.commit()
                logger.info(f"Created config for new guild {guild_id}")
        except IntegrityError:
            logger.warning(f"Config for guild {guild_id} already exists")
        except Exception as e:
            logger.error(f"Error creating guild config: {e}")
            raise

    def config_prefix_update(self, guild_id: int, prefix: str) -> None:
        """Add or update a guild's configured prefix.

        :param guild_id: Discord guild ID.
        :param prefix: New command prefix.
        """
        try:
            with self.get_session() as session:
                config = session.query(Config).filter(Config.guild_id == guild_id).first()
                if config:
                    config.prefix = prefix
                    session.commit()
                    logger.debug(f"Updated prefix for guild {guild_id}")
        except Exception as e:
            logger.error(f"Error updating prefix: {e}")
            raise

    def config_next_game_default_time_update(self, guild_id: int, default_time: str) -> None:
        """Add or update a guild's configured Next Game time.

        :param guild_id: Discord guild ID.
        :param default_time: New default time string.
        """
        try:
            with self.get_session() as session:
                config = session.query(Config).filter(Config.guild_id == guild_id).first()
                if config:
                    config.next_game_start = default_time
                    session.commit()
                    logger.debug(f"Updated next game default time for guild {guild_id}")
        except Exception as e:
            logger.error(f"Error updating next game default time: {e}")
            raise

    def config_next_game_default_interval_update(self, guild_id: int, default_interval: int) -> None:
        """Add or update a guild's configured default Next Game Interval.

        :param guild_id: Discord guild ID.
        :param default_interval: New default interval in days.
        """
        try:
            with self.get_session() as session:
                config = session.query(Config).filter(Config.guild_id == guild_id).first()
                if config:
                    config.next_game_interval = default_interval
                    session.commit()
                    logger.debug(f"Updated next game default interval for guild {guild_id}")
        except Exception as e:
            logger.error(f"Error updating next game default interval: {e}")
            raise

    def config_next_game_announce_channel(self, guild_id: int, announce_channel: str) -> None:
        """Update a server's configured channel for next game announcements.

        :param guild_id: Discord guild ID.
        :param announce_channel: Channel name for announcements.
        """
        try:
            with self.get_session() as session:
                config = session.query(Config).filter(Config.guild_id == guild_id).first()
                if config:
                    config.announce_channel = announce_channel
                    session.commit()
                    logger.debug(f"Updated announce channel for guild {guild_id}")
        except Exception as e:
            logger.error(f"Error updating announce channel: {e}")
            raise

    def config_load_guild(self, guild_id: int) -> Optional[Dict[str, Any]]:
        """Pull the saved config for the supplied guild_id.

        :param guild_id: Discord guild ID.
        :return: Dictionary of configuration values or None.
        """
        try:
            with self.get_session() as session:
                config = session.query(Config).filter(Config.guild_id == guild_id).first()
                if config:
                    result = {
                        "guild_id": config.guild_id,
                        "prefix": config.prefix,
                        "next_game_start": config.next_game_start,
                        "next_game_interval": config.next_game_interval,
                        "announce_channel": config.announce_channel,
                    }
                    logger.debug(f"Loaded config for guild {guild_id}")
                    return result
                return None
        except Exception as e:
            logger.error(f"Error loading guild config: {e}")
            return None

    def guild_remove_all(self, guild_id: int) -> None:
        """Function called when bot is removed from guild, cleans up all DB references.

        :param guild_id: Discord guild ID.
        """
        try:
            with self.get_session() as session:
                # Delete from all tables
                session.query(Config).filter(Config.guild_id == guild_id).delete()
                session.query(NextGame).filter(NextGame.guild_id == guild_id).delete()
                session.query(Quote).filter(Quote.guild_id == guild_id).delete()
                session.query(Initiative).filter(Initiative.guild_id == guild_id).delete()

                session.commit()
                logger.info(f"Removed all data for guild {guild_id}")
        except Exception as e:
            logger.error(f"Error removing guild data: {e}")
            raise


# Initialize the database instance
soulbot_db = DatabaseIO()
