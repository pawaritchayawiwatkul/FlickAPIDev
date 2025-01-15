from celery import shared_task

@shared_task
def send_notification(user_pk):
    print(user_pk)