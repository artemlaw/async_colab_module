import time
import asyncio
import ipywidgets as widgets
import pandas as pd
from IPython.display import display
from datetime import datetime, timedelta

from async_colab_module.tabstyle import TabStyles
from async_colab_module.utils import get_order_data_fbo


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


# Функция для запуска отчета
async def get_report(wb_client, base_dict, nm_ids_dict, from_date, to_date):
    progress_bar = ProgressBar(description='Формирование отчета:', bar_style='success')
    display(progress_bar)
    orders = await wb_client.get_orders(from_date)
    # TODO: Изменить на гейзер
    if from_date != to_date:
        time.sleep(20)
        orders.extend(await wb_client.get_orders(to_date))
    progress_bar.update(25)
    orders_ = [order for order in orders if order.get('orderType') == 'Клиентский'
               and not order.get('isCancel')
              #  and order.get('srid') not in rids
               and order.get('sticker') == '0']
    progress_bar.update(30)
    print(f'Получили заказов FBO за период: {len(orders_)}')

    orders_for_report = [
        get_order_data_fbo(order, nm_ids_dict[order.get('nmId')], base_dict)
        for order in orders_
        if order.get('nmId') in nm_ids_dict
    ]
    if orders_for_report:
        print(f'Формирую отчет по заказам от {from_date} до {to_date}')
        progress_bar.update(50)
        pd.set_option('display.max_columns', None)
        df = pd.DataFrame(orders_for_report)
        path_xls_file = 'wb_рентабельность_fbo.xlsx'
        # Возможно убрать и не хранить общую таблицу
        df.to_excel(path_xls_file, sheet_name='Список FBO', index=False)
        total_df = df.groupby('name').agg({
            'stock': 'min',
            'quantity': 'sum',
            'discount': 'max',
            'item_price': 'sum',
            'order_price': 'sum',
            'cost_price': 'sum',
            'commission': 'sum',
            'acquiring': 'sum',
            'logistics': 'sum',
            'reward': 'sum',
            'profit': 'sum',
            'order_reward': 'sum',
            'order_profit': 'sum'
        }).reset_index()
        # Рассчитать profitability
        total_df['profitability'] = round((total_df['profit'] / total_df['item_price']) * 100, 1)
        total_df['order_profitability'] = round((total_df['order_profit'] / total_df['order_price']) * 100, 1)
        total_df = pd.concat([total_df, pd.DataFrame(columns=['order_name', 'order_create', 'nm_id', 'article'])])

        overall_totals = df.agg({
            'stock': 'sum',
            'quantity': 'sum',
            'item_price': 'sum',
            'order_price': 'sum',
            'cost_price': 'sum',
            'commission': 'sum',
            'acquiring': 'sum',
            'logistics': 'sum',
            'reward': 'sum',
            'profit': 'sum',
            'order_reward': 'sum',
            'order_profit': 'sum'
        }).to_frame().T
        progress_bar.update(75)
        overall_totals['name'] = 'Итог'
        overall_totals['profitability'] = round((overall_totals['profit'] / overall_totals['item_price']) * 100, 1)
        overall_totals['order_profitability'] = round(
            (overall_totals['order_profit'] / overall_totals['order_price']) * 100, 1)
        overall_totals = overall_totals[['name', 'stock', 'quantity', 'item_price', 'order_price', 'cost_price',
                                         'commission', 'acquiring', 'logistics', 'reward', 'profit', 'profitability',
                                         'order_reward', 'order_profit', 'order_profitability']]
        # Определите желаемый порядок столбцов для объединенного DataFrame
        desired_column_order = ['name', 'nm_id', 'article', 'order_name', 'order_create', 'stock', 'quantity',
                                'discount', 'item_price', 'order_price', 'cost_price', 'commission', 'acquiring',
                                'logistics', 'reward', 'profit', 'profitability', 'order_reward', 'order_profit',
                                'order_profitability']
        # Объедините DataFrame с учетом столбцов в желаемом порядке и сортируя по name и order_name
        cascade_table = pd.concat([total_df[desired_column_order], df[desired_column_order]]) \
            .sort_values(by=['name', 'order_name']).reset_index(drop=True)

        cascade_table.loc[-1] = overall_totals.iloc[0]
        cascade_table.index = cascade_table.index + 1
        cascade_table = cascade_table.sort_index()
        tab_styles = TabStyles()
        progress_bar.update(85)
        with pd.ExcelWriter(path_xls_file, engine='openpyxl', mode='a') as writer:
            cascade_table.to_excel(writer, sheet_name='Сводная', index=False)

            wb = writer.book
            ws = wb['Сводная']
            # Установите ширину по умолчанию для всех столбцов (например, 15)
            ws.sheet_format.defaultColWidth = 10
            # Установите ширину для определенных столбцов
            ws.column_dimensions['A'].width = 30
            ws.column_dimensions['C'].width = 15
            ws.column_dimensions['D'].width = 12

            columns_to_align_right = [8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20]

            for row in range(2, ws.max_row + 1):
                order_name_cell = ws.cell(row=row, column=2)  # Столбец 'order_name' - второй столбец
                if order_name_cell.value:  # Если значение ячейки не пустое
                    for cell in ws[row]:
                        cell.style = tab_styles.row_l2_style
                    ws.row_dimensions[row].outline_level = 1
                    ws.row_dimensions.group(start=row, end=row, hidden=True)
                    ws.cell(row=row, column=17).style = tab_styles.col_spec_style
                    ws.cell(row=row, column=20).style = tab_styles.col_spec_style
                else:
                    for cell in ws[row]:
                        cell.style = tab_styles.row_l1_style
                    ws.cell(row=row, column=17).style = tab_styles.cell_l1_spec_style
                    ws.cell(row=row, column=20).style = tab_styles.cell_l1_spec_style

                for col in columns_to_align_right:
                    ws.cell(row=row, column=col).alignment = tab_styles.columns_to_align_right
                    ws.cell(row=row, column=col).number_format = '#,##0.0'  # Формат с одним знаком после запятой

            new_header = [
                'Наименование', 'NmID', 'Артикул', 'Заказ', 'Дата заказа', 'Остаток', 'Кол-во', 'Дисконт',
                'Цена товара', 'Цена заказа', 'Себест-ть', 'Комиссия', 'Эквайринг', 'Логистика', 'Вознагр-ние',
                'Прибыль', 'Рент-ть', 'Вознагр-ние за заказ', 'Прибыль за заказ', 'Рент-ть заказа'
            ]
            # Заменяем значения и определяем стиль в заголовке (первой строке)
            for i, value in enumerate(new_header):
                cell = ws.cell(row=1, column=i + 1)
                cell.value = value
                cell.style = tab_styles.header_row_spec_style if i in [16, 19] else tab_styles.header_row_style

                results_cell = ws.cell(row=2, column=i + 1)
                results_cell.style = tab_styles.header_row_spec_style

            # Автофильтры
            ws.auto_filter.ref = ws.dimensions
            # Зафиксировать ячейки
            ws.freeze_panes = 'B3'
        progress_bar.update(100)
        print('Файл отчета готов')
        files.download(path_xls_file)
    else:
        progress_bar.update(100)
        print('На указанный интервал нет данных для отчета')


# Функция для получения значения после ввода и проверки формата
async def submit_form(wb_client, base_dict, nm_ids_dict, from_input, to_input):
    from_input_value = from_input.value
    to_input_value = to_input.value
    try:
        # Проверяем корректность формата даты и времени
        from_date = datetime.strptime(from_input_value, '%Y-%m-%d %H:%M')
        to_date = datetime.strptime(to_input_value, '%Y-%m-%d %H:%M')
        await get_report(wb_client, base_dict, nm_ids_dict, from_date, to_date)
    except ValueError:
        print("Пожалуйста, введите корректную дату и время в формате YYYY-MM-DD HH:MM.")


def get_display_form(wb_client, base_dict, nm_ids_dict):
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
    # button.on_click(lambda b: submit_form(wb_client, base_dict, nm_ids_dict, from_input, to_input))

    def on_button_click(b):
        asyncio.create_task(submit_form(wb_client, base_dict, nm_ids_dict, from_input, to_input))

    button.on_click(on_button_click)
    # Отображаем элементы виджета
    display(from_input)
    display(to_input)
    display(button)
