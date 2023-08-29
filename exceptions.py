class Error(Exception):
    """Базовый класс для других исключений."""

    pass


class EmptyAnwserApiError(Error):
    """Пустой ответ от сервера."""

    pass


class WrongAnwserServerError(Error):
    """Неправильный ответ от сервера."""

    pass
