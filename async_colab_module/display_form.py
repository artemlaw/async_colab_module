import ipywidgets as widgets
from IPython.display import display
from datetime import datetime, timedelta
import time


class ProgressBar(widgets.IntProgress):
    def __init__(self, min_value=0, max_value=100, **kwargs):
        super().__init__(**kwargs)
        self.min = min_value
        self.max = max_value
        self.value = self.min

    def reset(self):
        self.value = self.min

    def update(self, value):
        self.value = value


# Функция для обновления прогресс-бара
def update_progress_bar(bar, value):
    bar.update(value)


# TODO: Удалить после так как будет импортирована из utils
def get_report(from_date, to_date):
    from_date = f'{from_date}.000'
    to_date = f'{to_date}.000'
    print(f'Формирую отчет по заказам от {from_date} до {to_date}')
    progress_bar = ProgressBar(description='Формирование отчета:', bar_style='success')
    display(progress_bar)
    update_progress_bar(progress_bar, 10)
    update_progress_bar(progress_bar, 50)
    update_progress_bar(progress_bar, 100)


# Функция для получения значения после ввода и проверки формата
def submit_form(from_input, to_input):
    from_input_value = from_input.value
    to_input_value = to_input.value
    try:
        # Проверяем корректность формата даты и времени
        from_date = datetime.strptime(from_input_value, '%Y-%m-%d %H:%M')
        to_date = datetime.strptime(to_input_value, '%Y-%m-%d %H:%M')
        get_report(from_date, to_date)
    except ValueError:
        print("Пожалуйста, введите корректную дату и время в формате YYYY-MM-DD HH:MM.")


def get_display_form():
    to_date = datetime.now().date()
    # Получаем вчерашний день (from_date)
    from_date = to_date - timedelta(days=1)
    # Создаем текстовое поля для ввода даты и времени
    from_input = widgets.Text(
        description='Период с:',
        placeholder='YYYY-MM-DD HH:MM',
        value=f'{from_date} 18:00'
    )
    to_input = widgets.Text(
        description='до:',
        placeholder='YYYY-MM-DD HH:MM',
        value=f'{to_date} 23:59'
    )
    # Кнопка для обработки значений формы и вызова основной функции
    button = widgets.Button(description="Сформировать отчет", button_style='info')
    button.on_click(lambda b: submit_form(from_input, to_input))

    # Отображаем виджет
    display(from_input)
    display(to_input)
    display(button)


if __name__ == '__main__':
    # Блок выполнения функции
    print('Запускаем программу')
    # MS_API_TOKEN = 'd7c6ef710489f9683336becc48d41b5b2e57da85'
    # client = MoySklad(MS_API_TOKEN)
    print('Подгружаем нужные справочники')
    # data_dict = get_dict_for_report(client)

    get_display_form()
