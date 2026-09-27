import vk_api
from config import TOKEN

try:
    vk_session = vk_api.VkApi(token=TOKEN)
    vk = vk_session.get_api()
    # Получаем информацию о сообществе
    group_info = vk.groups.getById(group_id=241611854)
    print("Токен рабочий. Сообщество:", group_info[0]["name"])
except Exception as e:
    print("Ошибка токена:", e)
