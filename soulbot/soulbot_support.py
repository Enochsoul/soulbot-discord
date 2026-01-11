"""Module containing support command for the main bot using SQLAlchemy ORM."""

import pathlib
import random
from typing import Dict, Optional, Sequence

import arrow
import sqlalchemy
from loguru import logger
from sqlalchemy import Boolean, Integer, String, Text, create_engine, delete, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, sessionmaker
from sqlalchemy.types import PickleType

# Timezone constants
MT = arrow.now("US/Mountain").tzinfo
PT = arrow.now("US/Pacific").tzinfo
CT = arrow.now("US/Central").tzinfo
ET = arrow.now("US/Eastern").tzinfo
UTC = arrow.utcnow().tzinfo


# SQLAlchemy setup
class Base(DeclarativeBase):
    pass


class NextGame(Base):
    """Next game schedule table."""

    __tablename__ = "next_game"

    guild_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    created_date: Mapped[int] = mapped_column(Integer, nullable=False)
    next_date: Mapped[int] = mapped_column(Integer, nullable=False)
    announce_on: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class Quote(Base):
    """Quotes table."""

    __tablename__ = "quotes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    guild_id: Mapped[int] = mapped_column(Integer, nullable=False)
    quote: Mapped[str] = mapped_column(Text, nullable=False)


class Initiative(Base):
    """Initiative tracker table."""

    __tablename__ = "initiative"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    guild_id: Mapped[int] = mapped_column(Integer, nullable=False)
    table: Mapped[PickleType] = mapped_column(PickleType, nullable=False)


class Config(Base):
    """Guild configuration table."""

    __tablename__ = "config"

    guild_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    prefix: Mapped[str] = mapped_column(String(10), nullable=False)
    next_game_start: Mapped[str] = mapped_column(String(20), nullable=False)
    next_game_interval: Mapped[int] = mapped_column(Integer, nullable=False)
    announce_channel: Mapped[str] = mapped_column(String(255), nullable=False)


class DatabaseIO:
    """Class definition to contain all interactions with the SQLAlchemy database."""

    def __init__(self, database_url: str):
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

    def init_db_add(self, guild_id: int, init_insert) -> None:
        """Insert/overwrite Initiative tracker data into the database.

        :param init_insert: List of tuples containing (guild_id, name, init) values.
        """
        try:
            with self.get_session() as session:
                # Clear existing records for the guild
                if init_insert:
                    session.execute(delete(Initiative).where(Initiative.guild_id == guild_id))

                # Add new record
                initiative = Initiative(guild_id=guild_id, table=init_insert)
                session.add(initiative)

                session.commit()
                logger.debug(f"Added {init_insert} initiative record.")
        except Exception as e:
            logger.error(f"Error adding initiative data: {e}")
            raise

    def init_db_reset(self, guild_id: int) -> None:
        """Delete initiative table data for a specific guild.

        :param guild_id: Discord guild ID.
        """
        try:
            with self.get_session() as session:
                session.execute(delete(Initiative).where(Initiative.guild_id == guild_id))
                session.commit()
                logger.debug(f"Reset initiative for guild {guild_id}.")
        except Exception as e:
            logger.error(f"Error resetting initiative data: {e}")
            raise

    def init_db_rebuild(self, guild_id: int):
        """Retrieve initiative table from the database to rebuild the bot data.

        :param guild_id: Discord guild ID.
        :return: List of tuples of all player/NPC names and initiative values.
        """
        try:
            with self.get_session() as session:
                select_stmt = select(Initiative.table).where(Initiative.guild_id == guild_id)
                results = session.execute(select_stmt).scalar_one_or_none()
                logger.debug(f"Retrieved initiative records for guild {guild_id}")
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
                select_stmt = (
                    select(Quote.quote).where(Quote.guild_id == guild_id).where(Quote.quote.contains(quote_search))
                )
                quotes = session.execute(select_stmt).scalars().all()
                if quotes:
                    random_quote = random.choice(quotes)
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
                # Get all quotes.
                select_stmt = select(Quote.quote).where(Quote.guild_id == guild_id)
                quotes = session.execute(select_stmt).scalars().all()

                if quotes:
                    quote = random.choice(quotes)
                    logger.debug(f"Retrieved random quote for guild {guild_id}")
                    return f'QUOTE: "{quote}"'
                else:
                    logger.debug(f"No quotes available for guild {guild_id}")
                    return "No quotes in the database."
        except Exception as e:
            logger.error(f"Error getting random quote: {e}")
            return "No quotes in the database."

    def next_game_db_get_date(self, guild_id: int) -> int:
        """Pull Next Game date from the database.

        :param guild_id: Discord guild ID.
        :return: Next Date in seconds from epoch.
        """
        try:
            with self.get_session() as session:
                select_stmt = select(NextGame.next_date).where(NextGame.guild_id == guild_id)
                result = session.execute(select_stmt).scalar()
                logger.debug(f"Retrieved next game data for guild {guild_id}")
                if result:
                    return result
                else:
                    raise RuntimeError("Error: No next game date found for guild.")
        except Exception as e:
            error_msg = f"Error getting next game date: {e}"
            logger.error(error_msg)
            raise RuntimeError(error_msg)

    def next_game_db_get_announce(self, guild_id: int) -> Optional[bool]:
        """Pull Next Game announce state from the database.

        :param guild_id: Discord guild ID.
        :return: boolean or None
        """
        try:
            with self.get_session() as session:
                select_stmt = select(NextGame.announce_on).where(NextGame.guild_id == guild_id)
                result = session.execute(select_stmt).scalar()
                logger.debug(f"Retrieved next game data for guild {guild_id}")
                return result
        except Exception as e:
            logger.error(f"Error getting next game date: {e}")
            return None

    def next_game_db_add(self, output_date: int, guild_id: int) -> None:
        """Replace current next game data with supplied new date.

        :param output_date: Unix timestamp of the next game.
        :param guild_id: Discord guild ID.
        """
        try:
            with self.get_session() as session:
                # Try to update existing record
                select_stmt = select(NextGame).where(NextGame.guild_id == guild_id)
                existing = session.execute(select_stmt).scalar()

                if existing:
                    session.execute(delete(NextGame).where(NextGame.guild_id == guild_id))

                # Create new record
                next_game = NextGame(
                    guild_id=guild_id, created_date=arrow.now(UTC).int_timestamp, next_date=output_date
                )
                session.add(next_game)

                session.commit()
                logger.debug(f"Updated next game date for guild {guild_id}")
        except Exception as e:
            logger.error(f"Error adding next game data: {e}")
            raise

    def next_game_announce_toggle(self, state: bool, guild_id: int) -> None:
        """Toggle the announce_on for the given guild ID.

        :param state: 0 or 1 (False or True).
        :param guild_id: Discord guild ID.
        """
        try:
            with self.get_session() as session:
                select_stmt = select(NextGame).where(NextGame.guild_id == guild_id)
                next_game = session.execute(select_stmt).scalar_one_or_none()
                if next_game:
                    next_game.announce_on = state
                    session.commit()
                    logger.debug(f"Toggled announcements to {state} for guild {guild_id}")
        except Exception as e:
            logger.error(f"Error toggling announcements: {e}")
            raise

    def config_get_guild(self, guild_id: int) -> Optional[Config]:
        """Get the default next game start time and interval from the config database.

        :param guild_id: Discord guild ID.
        :return: Tuple of (next_game_start, next_game_interval) or None.
        """
        try:
            with self.get_session() as session:
                select_stmt = select(Config).where(Config.guild_id == guild_id)
                result = session.execute(select_stmt).scalar_one_or_none()
                logger.debug(f"Retrieved next game defaults for guild {guild_id}")
                return result
        except Exception as e:
            logger.error(f"Error getting next game defaults: {e}")
            return None

    def next_game_get_all_announcing(self) -> Sequence[NextGame]:
        """Get all guilds that have announcements enabled.

        :return: List of tuples (guild_id, next_date).
        """
        try:
            with self.get_session() as session:
                select_stmt = select(NextGame).where(NextGame.announce_on)
                results = session.execute(select_stmt).scalars()
                logger.debug(f"Retrieved {len(results.all())} guilds with announcements enabled")
                return results.all()
        except Exception as e:
            logger.error(f"Error getting announcing guilds: {e}")
            return []

    def config_all_prefix_load(self) -> Dict[int, str]:
        """Load config settings for all registered guilds.

        :return: Dictionary mapping guild_id to prefix.
        """
        try:
            with self.get_session() as session:
                select_stmt = select(Config.guild_id, Config.prefix)
                results = session.execute(select_stmt).all()
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
                select_stmt = select(Config).where(Config.guild_id == guild_id)
                config = session.execute(select_stmt).scalar_one_or_none()
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
                select_stmt = select(Config).where(Config.guild_id == guild_id)
                config = session.execute(select_stmt).scalar_one_or_none()
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
                select_stmt = select(Config).where(Config.guild_id == guild_id)
                config = session.execute(select_stmt).scalar_one_or_none()
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
                select_stmt = select(Config).where(Config.guild_id == guild_id)
                config = session.execute(select_stmt).scalar_one_or_none()
                if config:
                    config.announce_channel = announce_channel
                session.commit()
                logger.debug(f"Updated announce channel for guild {guild_id}")
        except Exception as e:
            logger.error(f"Error updating announce channel: {e}")
            raise

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
db_file_path = str(pathlib.Path(__file__).parent.resolve()) + "/data/discordbot.sql"
logger.info(f"Setting up database at: {db_file_path}")
soulbot_db = DatabaseIO(f"sqlite:///{db_file_path}")
