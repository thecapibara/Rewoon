"""Entry point for the Rewoon desktop application."""

import config
import sound_player
import ui


def main() -> None:
    config.setup_logging()
    app_config = config.initialize()
    app = ui.AppUI(app_config=app_config, scheduler=sound_player.scheduler)
    app.run()


if __name__ == "__main__":
    main()
