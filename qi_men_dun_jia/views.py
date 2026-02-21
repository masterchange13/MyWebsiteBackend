from qi_men_dun_jia.services import qi_service

def calc(request):
    return qi_service.calc(request)

def analyze(request):
    return qi_service.analyze(request)
