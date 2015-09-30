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
create_following_relationship_query = '''INSERT INTO followers
                                         (follower_id, following_id)
                                         VALUES
                                         (%s, %s)
                                      '''


def follow(request):
    try:
        json_request = loads(request.body) 
    except ValueError as value_err:
        return HttpResponse(dumps({'code': codes.INVALID_QUERY,
                                   'response': str(value_err)}))
    
    try:
        follower = unicode(json_request['follower'])
        followee = unicode(json_request['followee'])
    except KeyError as key_err:
        return HttpResponse(dumps({'code': codes.INCORRECT_QUERY,
                                   'response': 'Not found: {}'.format(str(key_err))}))  

    # validate users
    users = [] 
    for email in [follower, followee]:
        try:
            user_id_qs = __cursor.execute(get_user_by_email_query, [email, ])  
        except DatabaseError as db_err: 
            return HttpResponse(dumps({'code': codes.UNKNOWN_ERR,
                                       'response': unicode(db_err)}))

        if not user_id_qs.rowcount:
             return HttpResponse(dumps({'code': codes.NOT_FOUND,
                                        'response': 'user with not found'}))
        user_id = user_id_qs.fetchone()[0]
        users.append(user_id)

    try:
        __cursor.execute(create_following_relationship_query, users)  
    except IntegrityError:
        pass
    except DatabaseError as db_err: 
        return HttpResponse(dumps({'code': codes.UNKNOWN_ERR,
                                   'response': unicode(db_err)}))  
    
    try:
        user = get_user_by_id(__cursor, users[0])
    except DatabaseError as db_err: 
        return HttpResponse(dumps({'code': codes.UNKNOWN_ERR,
                                   'response': unicode(db_err)})) 

    return HttpResponse(dumps({'code': codes.OK,
                               'response': user}))

## LIST FOLLOWERS ##
get_all_followers_query_prefix = '''SELECT user.id
                                    FROM user JOIN followers
                                    ON user.id = followers.follower_id
                                    WHERE following_id = %s 
                                 '''

def listFollowers(request):
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
    query = get_all_followers_query_prefix
    query_params = [user_id, ]
    since_id = general_utils.validate_id(request.GET.get('id'))
    if since_date:
        query += '''AND follower_id >= %s '''
        query_params.append(since_date)
    elif since_date == False and since_date is not None:
        return HttpResponse(dumps({'code': codes.INCORRECT_QUERY,
                                   'response': 'incorrect since_id fromat'}))

    order = request.GET.get('order', 'desc')
    if order.lower() not in ('asc', 'desc'):
        return HttpResponse(dumps({'code': codes.INCORRECT_QUERY,
                                   'response': 'incorrect order parameter: {}'.format(order)}))
    
    query += '''ORDER BY user.name''' + order

    limit = request.GET.get('limit')
    if limit:
        try:
            limit = int(limit)
        except ValueError:
             return HttpResponse(dumps({'code': codes.INCORRECT_QUERY,
                                        'response': 'limit should be int'}))
        query += ''' LIMIT %s'''
        query_params.append(limit)

    try:
        user_ids_qs = __cursor.execute(query, query_params)
    except DatabaseError as db_err: 
        return HttpResponse(dumps({'code': codes.UNKNOWN_ERR,
                                   'response': unicode(db_err)})) 
    
    followers = []
    if user_ids_qs.rowcount:
        for user_id in user_ids_qs.fetchall():
            try:
                user = get_user_by_id(__cursor, users[0])
            except DatabaseError as db_err: 
                return HttpResponse(dumps({'code': codes.UNKNOWN_ERR,
                                           'response': unicode(db_err)}))  
            followers.append(user)
    return HttpResponse(dumps({'code': codes.OK,
                               'response': followers})) 


## LIST FOLLOWINGS ##
get_all_followings_query_prefix = '''SELECT user.id
                                     FROM user JOIN followers
                                     ON user.id = followers.following_id
                                     WHERE follower_id = %s 
                                 '''

def listFollowings(request):
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
    query = get_all_followings_query_prefix
    query_params = [user_id, ]
    since_id = general_utils.validate_id(request.GET.get('id'))
    if since_date:
        query += '''AND following_id >= %s '''
        query_params.append(since_date)
    elif since_date == False and since_date is not None:
        return HttpResponse(dumps({'code': codes.INCORRECT_QUERY,
                                   'response': 'incorrect since_id fromat'}))

    order = request.GET.get('order', 'desc')
    if order.lower() not in ('asc', 'desc'):
        return HttpResponse(dumps({'code': codes.INCORRECT_QUERY,
                                   'response': 'incorrect order parameter: {}'.format(order)}))
    
    query += '''ORDER BY user.name''' + order

    limit = request.GET.get('limit')
    if limit:
        try:
            limit = int(limit)
        except ValueError:
             return HttpResponse(dumps({'code': codes.INCORRECT_QUERY,
                                        'response': 'limit should be int'}))
        query += ''' LIMIT %s'''
        query_params.append(limit)

    try:
        user_ids_qs = __cursor.execute(query, query_params)
    except DatabaseError as db_err: 
        return HttpResponse(dumps({'code': codes.UNKNOWN_ERR,
                                   'response': unicode(db_err)})) 
    
    followings = []
    if user_ids_qs.rowcount:
        for user_id in user_ids_qs.fetchall():
            try:
                user = get_user_by_id(__cursor, users[0])
            except DatabaseError as db_err: 
                return HttpResponse(dumps({'code': codes.UNKNOWN_ERR,
                                           'response': unicode(db_err)}))  
            followings.append(user)
    return HttpResponse(dumps({'code': codes.OK,
                               'response': followings})) 

## LIST POSTS ##
get_all_user_posts_query = '''SELECT post.date, post.dislikes, forum.short_name,
                               post.id, post.isApproved, post.isDeleted,
                               post.isEdited, post.isHighlighted, post.isSpam,
                               post.likes, post.message, post.parent,
                               post.likes - post.dislikes as points, post.thread_id
                               user.email
                        FROM post JOIN user ON post.user_id = user.id
                             JOIN forum ON forum.id = post.forum_id
                        WHERE user.id = %s '''

def listPosts(request):
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
    query_params = [user_id, ]
    get_post_list_specified_query = get_all_user_posts_query
    since_date = general_utils.validate_date(request.GET.get('since'))
    if since_date:
        get_all_forum_posts_specified_query += '''AND post.date >= %s '''
        query_params.append(since_date)
    elif since_date == False and since_date is not None:
        return HttpResponse(dumps({'code': codes.INCORRECT_QUERY,
                                   'response': 'incorrect since_date fromat'}))

    order = request.GET.get('order', 'desc')
    if order.lower() not in ('asc', 'desc'):
        return HttpResponse(dumps({'code': codes.INCORRECT_QUERY,
                                   'response': 'incorrect order parameter: {}'.format(order)}))
    
    get_post_list_specified_query += '''ORDER BY post.date ''' + order

    limit = request.GET.get('limit')
    if limit:
        try:
            limit = int(limit)
        except ValueError:
             return HttpResponse(dumps({'code': codes.INCORRECT_QUERY,
                                        'response': 'limit should be int'}))
        get_post_list_specified_query += ''' LIMIT %s'''
        query_params.append(limit)

    try:
        post_list_qs = __cursor.execute(get_post_list_query.format(related_table_name), query_params)
    except DatabaseError as db_err: 
        return HttpResponse(dumps({'code': codes.UNKNOWN_ERR,
                                   'response': unicode(db_err)})) 
    
    posts = []

    for post in post_list_qs.fetchall():
        posts.append({
            "date": post[0],
            "dislikes": post[1],
            "forum": post[2],
            "id": post[3],
            "isApproved": post[4],
            "isDeleted": post[5],
            "isEdited": post[6],
            "isHighlighted": post[7],
            "isSpam": post[8],
            "likes": post[9],
            "message": post[10],
            "parent": post[11],
            "points": post[12],
            "thread": post[13],
            "user": post[14]
        })
    return HttpResponse(dumps({'code': codes.OK,
                               'response': posts})) 

## UNFOLLOW ##
delete_following_relationship_query = '''DELETE FROM followers
                                         WHERE follower_id = %s
                                         AND following_id = %s    
                                      '''


def unfollow(request):
    try:
        json_request = loads(request.body) 
    except ValueError as value_err:
        return HttpResponse(dumps({'code': codes.INVALID_QUERY,
                                   'response': str(value_err)}))
    
    try:
        follower = unicode(json_request['follower'])
        followee = unicode(json_request['followee'])
    except KeyError as key_err:
        return HttpResponse(dumps({'code': codes.INCORRECT_QUERY,
                                   'response': 'Not found: {}'.format(str(key_err))}))  

    # validate users
    users = [] 
    for email in [follower, followee]:
        try:
            user_id_qs = __cursor.execute(get_user_by_email_query, [email, ])  
        except DatabaseError as db_err: 
            return HttpResponse(dumps({'code': codes.UNKNOWN_ERR,
                                       'response': unicode(db_err)}))

        if not user_id_qs.rowcount:
             return HttpResponse(dumps({'code': codes.NOT_FOUND,
                                        'response': 'user with not found'}))
        user_id = user_id_qs.fetchone()[0]
        users.append(user_id)

    try:
        __cursor.execute(delete_following_relationship_query, users)  
    except DatabaseError as db_err: 
        return HttpResponse(dumps({'code': codes.UNKNOWN_ERR,
                                   'response': unicode(db_err)}))  
    
    try:
        user = get_user_by_id(__cursor, users[0])
    except DatabaseError as db_err: 
        return HttpResponse(dumps({'code': codes.UNKNOWN_ERR,
                                   'response': unicode(db_err)})) 

    return HttpResponse(dumps({'code': codes.OK,
                               'response': user}))

## UPDATE PROFILE ##
update_profile_query = '''UPDATE user
                          SET about = %,
                              name = %s,
                          WHERE email = %s;
                          SELECT id FROM user
                          WHERE email = %s;'''

def updateProfile(request):
    try:
        json_request = loads(request.body) 
    except ValueError as value_err:
        return HttpResponse(dumps({'code': codes.INVALID_QUERY,
                                   'response': str(value_err)}))
    
    try:
        about = unicode(json_request['about'])
        name = unicode(json_request['message'])
        email = unicode(json_request['user'])
    except KeyError as key_err:
        return HttpResponse(dumps({'code': codes.INCORRECT_QUERY,
                                   'response': 'Not found: {}'.format(str(key_err))}))    


    try:
        user_qs = __cursor.execute(update_profile_query, [about, name, emai, email])
    except DatabaseError as db_err: 
        return HttpResponse(dumps({'code': codes.UNKNOWN_ERR,
                                   'response': str(db_err)}))
 
    user_id = user_qs.fetchone()[0]
    try:
        user = get_user_by_id(__cursor, user_id)
    except DatabaseError as db_err: 
        return HttpResponse(dumps({'code': codes.UNKNOWN_ERR,
                                   'response': unicode(db_err)})) 

    return HttpResponse(dumps({'code': codes.OK,
                               'response': user}))    

