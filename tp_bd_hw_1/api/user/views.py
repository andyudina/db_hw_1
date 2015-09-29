from json import dumps

from django.db import connection, DatabaseError, IntegrityError, transaction
from django.http import HttpResponse

from general import codes, utils as general_utils
from .utils import get_user_by_id
from thread.utils import get_thread_by_id
from post.utils import get_post_by_id
from forum.utils import get_forum_by_id

__cursor = connection.cursor()

related_functions_dict = {
                          'user': get_user_by_id,
                          'thread': get_thread_by_id,
                          'forum': get_forum_by_id
                          }

## CREATE ##
create_user_query = u''' INSERT INTO user
                         (username, about, name, emai)
                         VALUES
                         (%s, %s, %s, %s);
                         SELECT LAST_INSERT_ID();
                     '''
update_user_query = '''UPDATE  user SET isAnonymous = %s 
                       WHERE id = %s '''
                              
def create(request):
    try:
        json_request = loads(request.body) 
    except ValueError as value_err:
        return HttpResponse(dumps({'code': codes.INVALID_QUERY,
                                   'response': str(value_err)}))
    
    try:
        username = unicode(json_request['username'])
        about = unicode(json_request['about'])
        name = unicode(json_request['message'])
        email = unicode(json_request['email'])
    except KeyError as key_err:
        return HttpResponse(dumps({'code': codes.INCORRECT_QUERY,
                                   'response': 'Not found: {}'.format(str(key_err))}))    


    try:
        user_qs = __cursor.execute(create_user_query, [username, about, name, emai])
    except IntegrityError:
        return HttpResponse(dumps({'code': codes.USER_ALREADY_EXISTS,
                                   'response': 'user already exists'})) 

    except DatabaseError as db_err: 
        return HttpResponse(dumps({'code': codes.UNKNOWN_ERR,
                                   'response': str(db_err)}))
 
    user_id = user_qs.fetchone()[0]
    user = {"about": about,
            "email": email,
            "id": user_id,
            "isAnonymous": False,
            "name": name,
            "username": username
             }     
    try:
        isAnonymous = json_request['isAnonymous'] 
        if not isinstance(isAnonymous, bool):
            return HttpResponse(dumps({'code': codes.INCORRECT_QUERY,
                                       'response': 'isAnonymous flag should be bool'}))
    except KeyError:
        return HttpResponse(dumps({'code': codes.OK,
                                   'response': user}))
    try
        __cursor.execute(update_user_query, [isAnonymous, user_id])
    except DatabaseError as db_err: 
        return HttpResponse(dumps({'code': codes.UNKNOWN_ERR,
                                   'response': str(db_err)}))

    user["isAnonymous"] = isAnonymous 

    return HttpResponse(dumps({'code': codes.OK,
                               'response': user}))

## DETAILS ##
get_user_by_email_query = '''SELECT id FROM user
                             WHERE email = %s;
                          '''
def details(request):
   if request.method != 'GET':
        return HttpResponse(dumps({'code': codes.INVALID_QUERY,
                                   'response': 'request method should be GET'}))
    email = request.GET.get('user')
    # validate user
    try:
        user_id_qs = __cursor.execute(get_user_by_email_query, [email, ])  
    except DatabaseError as db_err: 
        return HttpResponse(dumps({'code': codes.UNKNOWN_ERR,
                                   'response': unicode(db_err)}))

    if not user_id_qs.rowcount:
        return HttpResponse(dumps({'code': codes.NOT_FOUND,
                                   'response': 'user not found'}))
    user_id = user_id_qs.fetchone()[0]

    try:
        user = get_user_by_id(__cursor, user_id)
    except DatabaseError as db_err: 
        return HttpResponse(dumps({'code': codes.UNKNOWN_ERR,
                                   'response': unicode(db_err)}))

    return HttpResponse(dumps({'code': codes.OK,
                               'response': user}))    

## FOLLOW ##
create_following_relationship_query = '''
                                      '''
def follow(request):
    result = {}
    return HttpResponse(dumps(result))

def listFollowers(request):
    result = {}
    return HttpResponse(dumps(result))

def listFollowing(request):
    result = {}
    return HttpResponse(dumps(result))

def listPosts(request):
    result = {}
    return HttpResponse(dumps(result))

def unfollow(request):
    result = {}
    return HttpResponse(dumps(result))

def updateProfile(request):
    result = {}
    return HttpResponse(dumps(result))

