from collections import Counter

from fastapi import FastAPI, WebSocket

# from Sort import Tracker
from cb_5.track_1 import track_data, country_balls_amount
import asyncio
import glob

app = FastAPI(title='Tracker assignment')
imgs = glob.glob('imgs/*')
country_balls = [{'cb_id': x, 'img': imgs[x % len(imgs)]} for x in range(country_balls_amount)]
print('Started')

PREV_BOXES = {}
# tracker = Tracker()


def tracker_soft(el):
    """
    Необходимо изменить у каждого словаря в списке значение поля 'track_id' так,
    чтобы как можно более длительный период времени 'track_id' соответствовал
    одному и тому же кантри болу.

    Исходные данные: координаты рамки объектов

    Ограничения:
    - необходимо использовать как можно меньше ресурсов (представьте, что
    вы используете embedded устройство, например Raspberri Pi 2/3).
    -значение по ключу 'cb_id' является служебным, служит для подсчета метрик качества
    вашего трекера, использовать его в алгоритме трекера запрещено
    - запрещается присваивать один и тот же track_id разным объектам на одном фрейме
    """
    # Словарь для хранения предыдущих Bounding box
    # prev_boxes = {}
    if len(PREV_BOXES) != 0:
        for prev_box in PREV_BOXES.values():
            prev_box[2] = False
    # Перебираем каждый объект в кадре
    for obj in el['data']:
        is_updated = False
        # Получаем текущий Bounding box объекта
        box = [obj['bounding_box'], obj['track_id'], is_updated]
        if len(box[0]) == 0:
            obj['track_id'] = '?'

        # Проверяем, если у объекта еще нет присвоенного track_id
        if obj['track_id'] is None:
            # Проверяем, если объект уже существует в предыдущих Bounding box
            # Проверяем, если IoU больше заданного порога
            iou, track = compute_all_iou(box)
            if iou >= 0.2:
                obj['track_id'] = track
                box[2] = True
            else:
                distance, track = compute_all_distance(box)
                if distance < 80:
                    obj['track_id'] = track
                    box[2] = True
            if obj['track_id'] is None:
                for track_id, prev_box in PREV_BOXES.items():
                    if not prev_box[2]:
                        distance, track = compute_all_distance(box, False)
                        if distance < 300:
                            obj['track_id'] = track
                            box[2] = True

            # Если объект не найден в предыдущих Bounding box, создаем новый track_id
            if obj['track_id'] is None:
                obj['track_id'] = len(PREV_BOXES)
                box[2] = True
                PREV_BOXES[obj['track_id']] = box

        # Обновляем предыдущий Bounding box объекта
        if obj['track_id'] != '?':
            PREV_BOXES[obj['track_id']] = box

    # Выводим обновленный список объектов с присвоенными track_id
    return el


def tracker_strong(el):
    """
    Необходимо изменить у каждого словаря в списке значение поля 'track_id' так,
    чтобы как можно более длительный период времени 'track_id' соответствовал
    одному и тому же кантри болу.

    Исходные данные: координаты рамки объектов, скриншоты прогона

    Ограничения:
    - вы можете использовать любые доступные подходы, за исключением
    откровенно читерных, как например захардкодить заранее правильные значения
    'track_id' и т.п.
    - значение по ключу 'cb_id' является служебным, служит для подсчета метрик качества
    вашего трекера, использовать его в алгоритме трекера запрещено
    - запрещается присваивать один и тот же track_id разным объектам на одном фрейме

    P.S.: если вам нужны сами фреймы, измените в index.html значение make_screenshot
    на true для первого прогона, на повторном прогоне можете читать фреймы из папки
    и по координатам вырезать необходимые регионы.
    """


    # for obj in el['data']:
    #     # Получаем текущий Bounding box объекта
    #     box = obj['bounding_box']
    #     x = obj['x']
    #     y = obj['y']
    #     if obj['track_id'] is None:
    #         # Обновляем трекер с текущим Bounding box
    #         tracker.update(box, x, y)
    #         # Перебираем треки и присваиваем объекту track_id трека
    #         for track in tracker.tracks:
    #             obj['track_id'] = track.track_id
    # return el


def compute_iou(box1, box2):
    x1, y1, w1, h1 = box1[0]
    x2, y2, w2, h2 = box2[0]
    cx1 = ((x1 + w1)/2)
    cy1 = ((y1 + h1)/2)
    cx2 = ((x2 + w2)/2)
    cy2 = ((y2 + h2)/2)

    if x1 > x2 + w2 or x2 > x1 + w1 or y1 > y2 + h2 or y2 > y1 + h1:
        return 0

    distance = ((cx2 - cx1) ** 2 + (cy2 - cy1) ** 2) ** 0.5

    # Вычисляем координаты границ Bounding box
    x_left = max(x1, x2)
    y_top = max(y1, y2)
    x_right = min(w1, w2)
    y_bottom = min(h1, h2)

    # Вычисляем площади пересечения и объединения Bounding box
    i_height = max(y_bottom - y_top, 0)
    i_weight = max(x_right - x_left, 0)
    # intersection_area = max(0, ((x_right - x_left) * (y_bottom - y_top)))
    intersection_area = i_weight * i_height

    gt_height = h1 - y1
    gt_weight = w1 - x1

    pd_height = h2 - y2
    pd_weight = w2 - x2
    union_area = gt_weight * gt_height + pd_weight * pd_height - intersection_area
    # union_area = (((w1 - x1) * (h1 - y1)) + ((w2 - x2) * (h2 - y2))) - intersection_area
    # c = (((x2 - x1) ** 2) + ((y2 - y1) ** 2)) ** 0.5
    c = (max(w1, w2) ** 2 + max(h1, h2) ** 2) ** 0.5
    # Вычисляем IoU
    iou = intersection_area / union_area
    # alpha = 0.5
    # diou = ((distance / c) + alpha) * (1 - iou)
    diou = (iou + ((distance**2)/(c**2)))
    if iou == 0:
        return iou
    else:
        return round(max(iou, diou), 1)


def compute_all_iou(box):
    max_iou = 0
    box_track_id = None

    for prev_box in PREV_BOXES.values():
        if len(prev_box[0]) != 0:
            iou = compute_iou(box, prev_box)
            if iou > max_iou:
                max_iou = iou
                box_track_id = prev_box[1]

    # print("Max iou:", max_iou)
    # print("Track ID:", box_track_id)
    return max_iou, box_track_id


def compute_distance(box1, box2):
    x1, y1, w1, h1 = box1[0]
    x2, y2, w2, h2 = box2[0]
    cx1 = ((x1 + w1) / 2)
    cy1 = ((y1 + h1) / 2)
    cx2 = ((x2 + w2) / 2)
    cy2 = ((y2 + h2) / 2)

    distance = ((cx2 - cx1) ** 2 + (cy2 - cy1) ** 2) ** 0.5

    return distance


def compute_all_distance(box, flag=True):
    min_distance = float('inf')
    min_track_id = None

    if flag is True:
        for track_id, prev_box in PREV_BOXES.items():
            distance = compute_distance(box, prev_box)
            if distance < min_distance:
                min_distance = distance
                min_track_id = track_id
    else:
        for track_id, prev_box in PREV_BOXES.items():
            if not prev_box[2]:
                distance = compute_distance(box, prev_box)
                if distance < min_distance:
                    min_distance = distance
                    min_track_id = track_id


    # print("Min Distance:", min_distance)
    # print("Track ID:", min_track_id)

    return min_distance, min_track_id


def aggreagtre_data(el, id_entrance):
    for x in el['data']:
        if type(x['track_id']) is int:
            if x['cb_id'] in id_entrance:
                id_entrance[x['cb_id']].append(x['track_id'])
            else:
                id_entrance[x['cb_id']] = [x['track_id']]
    # print("Entrance:", id_entrance)
    return id_entrance


def calc_tracker_metrics(id_entrance):
    total_length = 0
    right_choice = 0
    for k, v in id_entrance.items():
        max_occur_value, amount_of_entrance = Counter(v).most_common(1)[0]
        if max_occur_value is None:
            amount_of_entrance = 0
        total_length += len(v)
        right_choice += amount_of_entrance
        print(f'Track: {k=} quality {amount_of_entrance / len(v)}')
    print(f'Overall {right_choice / total_length}')


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    print('Accepting client connection...')
    await websocket.accept()
    # отправка служебной информации для инициализации объектов
    # класса CountryBall на фронте
    await websocket.send_text(str(country_balls))
    id_entrance = {}
    for el in track_data:
        await asyncio.sleep(0.2)
        # TODO: part 1
        el = tracker_soft(el)
        # TODO: part 2
        # el = tracker_strong(el)
        # отправка информации по фрейму
        await websocket.send_json(el)
        id_entrance = aggreagtre_data(el, id_entrance)
    calc_tracker_metrics(id_entrance)
    print('Bye..')
