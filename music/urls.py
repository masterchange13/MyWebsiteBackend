from django.urls import path
from music import views

# export const musicApi = {
#     // 获取音乐列表
#     getMusicList: (params) => request.get('/music/list', {params}),
#     // 添加音乐
#     addMusic: (data) => request.post('/music/add', data),
#     // 修改音乐
#     updateMusic: (data) => request.post('/music/update', data),
#     removeMusic: (data) => request.delete('/music/remove', { data }),
#     getAllMusic: () => request.get('/music/getAll'),
#     updateMusicStatus: (data) => request.post('/music/updateMusicStatus', data),
# }

urlpatten = [
    path('list', views.get_music_list),
    path('add', views.add_music),
    path('update', views.update_music),
    path('remove', views.remove_music),
    path('get_all', views.get_all_music),
    path('update_music_status', views.update_music_status),
    path('upload', views.upload_music),
]

media_url = [
    path('audio/<str:filename>', views.get_audio),
    path('covers/<str:filename>', views.get_cover),
]