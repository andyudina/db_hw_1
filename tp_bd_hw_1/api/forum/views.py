from json import dumps, loads

from django.db import connection, DatabaseError, IntegrityError
from django.views.decorators.csrf import csrf_exempt
from django.http import HttpResponse

from api.general import codes, utils as general_utils
from api.user.utils import get_user_by_id
from api.thread.utils import get_thread_by_id
from api.forum.utils import get_forum_by_id
from api.post.utils import get_post_by_id

related_functions_dict = {'user': get_user_by_id,
                          'thread': get_thread_by_id,
                          'forum': get_forum_by_id
                          }


## CREATE ##
create_forum_query = u'''INSERT INTO forum
                        (name, short_name, user_id)
                        VALUES
                        (%s, %s, %s);
                      '''

select_last_insert_id =  '''
                         SELECT LAST_INSERT_ID();
                         '''

get_user_by_email_query = '''SELECT id FROM user
                             WHERE email = %s;
                          '''

get_forum_by_short_name_query = u'''SELECT forum.id, forum.name, forum.short_name, user.email, user.id
                                   FROM forum INNER JOIN user
                                   ON forum.user_id = user.id
                                   WHERE forum.short_name = %s;
                                ''' 

@csrf_exempt
def create(request):
    __cursor = connection.cursor()
    try:
        json_request = loads(request.body) 
    except ValueError as value_err:
        __cursor.close()
        return HttpResponse(dumps({'code': codes.INVALID_QUERY,
                                   'response': unicode(value_err)}))
    
    try:
        name = json_request['name']
        short_name = json_request['short_name']
        email = json_request['user']
    except KeyError as key_err:
        __cursor.close()
        return HttpResponse(dumps({'code': codes.INCORRECT_QUERY,
                                   'response': 'Not found: {}'.format(unicode(key_err))}))    
   
    try:
        user_id_qs = __cursor.execute(get_user_by_email_query, [email, ]) 
    except DatabaseError as db_err: 
        __cursor.close()
        return HttpResponse(dumps({'code': codes.UNKNOWN_ERR,
                                   'response': unicode(db_err)}))

    if not __cursor.rowcount:
        __cursor.close()
        return HttpResponse(dumps({'code': codes.NOT_FOUND,
                                   'response': 'user not found'}))

    user_id = __cursor.fetchone()[0]
    try:
        __cursor.execute(create_forum_query, [name, short_name, user_id])
        __cursor.execute(select_last_insert_id, [])
        forum_id = __cursor.fetchone()[0]
        __cursor.close()
        return HttpResponse(dumps({'code': codes.OK,
                                   'response': {
                                        'id': forum_id,
                                        'name': name,
                                        'short_name': short_name,
                                        'user': email
                                         }}))
    except IntegrityError:
        __cursor.execute(get_forum_by_short_name_query, [short_name, ])
        existed_forum = __cursor.fetchone()
        __cursor.close()
        return HttpResponse(dumps({'code': codes.OK,
                                   'response': {
                                        'id': existed_forum[0],
                                        'name': existed_forum[1],
                                        'short_name': existed_forum[2],
                                        'user': existed_forum[3]
                                         }}))
    except DatabaseError as db_err: 
        __cursor.close()
        return HttpResponse(dumps({'code': codes.UNKNOWN_ERR,
                                   'response': unicode(db_err)}))

      
## DETAILS ##
def details(request):
  try:
    __cursor = connection.cursor()
    if request.method != 'GET':
        __cursor.close()
        return HttpResponse(dumps({'code': codes.INVALID_QUERY,
                                   'response': 'request method should be GET'}))
    short_name = request.GET.get('forum')
    if not short_name:
        __cursor.close()
        return HttpResponse(dumps({'code': codes.INVALID_QUERY,
                                   'response': 'forum name not found'})) 
    try:
        __cursor.execute(get_forum_by_short_name_query, [short_name, ]) 
        if not __cursor.rowcount:
             __cursor.close()
             return HttpResponse(dumps({'code': codes.NOT_FOUND,
                                        'response': 'forum not found'}))
    except DatabaseError as db_err:
        __cursor.close() 
        return HttpResponse(dumps({'code': codes.UNKNOWN_ERR,
                                   'response': unicode(db_err)}))
    forum = __cursor.fetchone()
    response = {"id": forum[0],
                "name": forum[1],
                "short_name": forum[2]
               }

    related = request.GET.get('related')
    if related:
        if related != 'user':
            __cursor.close()
            return HttpResponse(dumps({'code': codes.INCORRECT_QUERY,
                                       'response': 'incorrect related parameter: {}'.format(related)}))
        user_id = forum[4]
        try:
            user, related_ids = get_user_by_id(__cursor, user_id)
        except DatabaseError as db_err: 
            __cursor.close()
            return HttpResponse(dumps({'code': codes.UNKNOWN_ERR,
                                       'response': unicode(db_err)}))
        response['user'] = user
        
    else:
        response["user"] = forum[3]  
        __cursor.close()       
    return HttpResponse(dumps({'code': codes.OK,
                               'response': response}))
  except Exception as e:
      print e

## List POSTS ##
get_all_forum_posts_query = '''SELECT post.date, post.dislikes, forum.short_name,
                                      post.id, post.isApproved, post.isDeleted, post.isEdited,
                                      post.isHighlighted, post.isSpam, post.likes, post.message, post.parent,
                                      post.likes - post.dislikes as points, post.thread_id, user.email,
                                      forum.id, thread.id, user.id
                                FROM post INNER JOIN forum ON post.forum_id = forum.id
                                INNER JOIN user ON user.id = post.user_id
                                WHERE post.forum_id = %s
                            '''
def listPosts(request):
    __cursor = connection.cursor()
    if request.method != 'GET':
        __cursor.close()
        return HttpResponse(dumps({'code': codes.INVALID_QUERY,
                                   'response': 'request method should be GET'}))
    short_name = request.GET.get('forum')
    if not short_name:
        __cursor.close()
        return HttpResponse(dumps({'code': codes.INCORRECT_QUERY,
                                   'response': 'forum name not found'})) 
    try:
        forum_qs = __cursor.execute(get_forum_by_short_name_query, [short_name, ])#.fetchone() 
        if not __cursor.rowcount:
             __cursor.close()
             return HttpResponse(dumps({'code': codes.NOT_FOUND,
                                        'response': 'forum not found'}))
    except DatabaseError as db_err: 
        __cursor.close()
        return HttpResponse(dumps({'code': codes.UNKNOWN_ERR,
                                   'response': unicode(db_err)}))
    forum_id = __cursor.fetchone()[0]

    get_all_forum_posts_specified_query = get_all_forum_posts_query
    query_params = [forum_id, ]
    since_date = general_utils.validate_date(request.GET.get('since'))
    if since_date:
        get_all_forum_posts_specified_query += '''AND post.date >= %s '''
        query_params.append(since_date)
    elif since_date == False and since_date is not None:
        __cursor.close()
        return HttpResponse(dumps({'code': codes.INCORRECT_QUERY,
                                   'response': 'incorrect since_date fromat'}))

    order = request.GET.get('order', 'desc')
    if order.lower() not in ('asc', 'desc'):
        __cursor.close()
        return HttpResponse(dumps({'code': codes.INCORRECT_QUERY,
                                   'response': 'incorrect order parameter: {}'.format(order)}))
    
    get_all_forum_posts_specified_query += '''ORDER BY post.date ''' + order

    limit = request.GET.get('limit')
    if limit:
        try:
            limit = int(limit)
        except ValueError:
             __cursor.close()
             return HttpResponse(dumps({'code': codes.INCORRECT_QUERY,
                                        'response': 'limit should be int'}))
        get_all_forum_posts_specified_query += ''' LIMIT %s'''
        query_params.append(limit)

    try:
        posts_qs = __cursor.execute(get_all_forum_posts_specified_query, query_params) 
    except DatabaseError as db_err: 
        __cursor.close()
        return HttpResponse(dumps({'code': codes.UNKNOWN_ERR,
                                   'response': unicode(db_err)})) 
    
    related = set(request.GET.getlist('related'))
    posts = []
    for post in posts_qs.fetchall():
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

        related_ids = {'forum': post[15],
                       'thread': post[16],
                       'user': post[17]
                       }

        for related_ in filter(lambda x: x in related_functions_dict.keys(), related):
            get_related_info_func = related_functions_dict[related_]
            posts[-1][related_], related_ids_ = get_related_info_func(__cursor, related_ids[related_])
    __cursor.close()            
    return HttpResponse(dumps({'code': codes.OK,
                               'response': posts
                               }))

## LIST THREADS ##
get_all_forum_threads_query = '''SELECT thread.date, thread.dislikes, forum.short_name,
                                        thread.id, thread.isClosed, thread.isDeleted, 
                                        thread.likes, thread.message,
                                        thread.likes - thread.dislikes as points, posts.count as posts, 
                                        thread.slug, thread.title, thread.user.email,
                                        forum.id,  user.id
                                 FROM thread INNER JOIN forum ON thread.forum_id = forum.id
                                 INNER JOIN user ON user.id = thread.user_id
                                 INNER JOIN (SELECT thread_id, COUNT(*) as count
                                             FROM posts
                                             GROUP BY thread_id) posts ON posts.thread_id = thread.id
                                 WHERE thread.forum_id = %s
                            '''
def listThreads(request):
    __cursor = connection.cursor()
    if request.method != 'GET':
        __cursor.close()
        return HttpResponse(dumps({'code': codes.INVALID_QUERY,
                                   'response': 'request method should be GET'}))
    short_name = request.GET.get('forum')
    if not short_name:
        __cursor.close()
        return HttpResponse(dumps({'code': codes.INCORRECT_QUERY,
                                   'response': 'forum name not found'})) 
    try:
        forum_qs = __cursor.execute(get_forum_by_short_name_query, [short_name, ])
        if not __cursor.rowcount:
             __cursor.close()
             return HttpResponse(dumps({'code': codes.NOT_FOUND,
                                        'response': 'forum not found'}))
    except DatabaseError as db_err: 
        __cursor.close()
        return HttpResponse(dumps({'code': codes.UNKNOWN_ERR,
                                   'response': unicode(db_err)}))
    forum_id = __cursor.fetchone()[0]

    get_all_forum_threads_specified_query = get_all_forum_threads_query
    query_params = [forum_id, ]
    since_date = general_utils.validate_date(request.GET.get('since'))
    if since_date:
        get_all_forum_threads_specified_query += '''AND date >= %s '''
        query_params.append(since_date)
    elif since_date == False and since_date is not None:
        __cursor.close()
        return HttpResponse(dumps({'code': codes.INCORRECT_QUERY,
                                   'response': 'incorrect since_date fromat'}))
 
    order = request.GET.get('order', 'desc')
    if order.lower() not in ('asc', 'desc'):
        __cursor.close()
        return HttpResponse(dumps({'code': codes.INCORRECT_QUERY,
                                   'response': 'incorrect order parameter: {}'.format(order)}))
    
    get_all_forum_threads_specified_query += '''ORDER BY thread.date ''' + order

    limit = request.GET.get('limit')
    if limit:
        try:
            limit = int(limit)
        except ValueError:
             __cursor.close()
             return HttpResponse(dumps({'code': codes.INCORRECT_QUERY,
                                        'response': 'limit should be int'}))
        get_all_forum_threads_specified_query += ''' LIMIT %s'''
        query_params.append(limit)

    try:
        threads_qs = __cursor.execute(get_all_forum_threads_specified_query, query_params) 
    except DatabaseError as db_err: 
        __cursor.close()
        return HttpResponse(dumps({'code': codes.UNKNOWN_ERR,
                                   'response': unicode(db_err)})) 
    
    related = set(request.GET.getlist('related'))
    threads = []
    for thread in __cursor.fetchall():
        threads.append({
            "date": thread[0],
            "dislikes": thread[1],
            "forum": thread[2],
            "id": thread[3],
            "isClosed": thread[4],
            "isDeleted": thread[5],
            "likes": thread[6],
            "message": thread[7],
            "points": thread[8],
            "posts": thread[9], 
            "slug": thread[10],
            "title": thread[11],
            "user": thread[12]
            })

        related_ids = {'forum': thread[13],
                       'user': thread[14]
                       }

        for related_ in filter(lambda x: x in related_functions_dict.keys() and x != 'thread', related):
            get_related_info_func = related_functions_dict[related_]
            threads[-1][related_], related_ids_ = get_related_info_func(__cursor, related_ids[related_])      
    __cursor.close()        
    return HttpResponse(dumps({'code': codes.OK,
                               'response': threads
                               }))

## LIST USERS ##
get_all_forum_users_query = '''SELECT user.id
                               FROM user INNER JOIN post
                               ON user.id = post.user_id
                               WHERE post.forum_id = %s
                            '''
def listUsers(request):
    __cursor = connection.cursor()
    if request.method != 'GET':
        __cursor.close()
        return HttpResponse(dumps({'code': codes.INVALID_QUERY,
                                   'response': 'request method should be GET'}))
    short_name = request.GET.get('forum')
    if not short_name:
        __cursor.close()
        return HttpResponse(dumps({'code': codes.INCORRECT_QUERY,
                                   'response': 'forum name not found'})) 
    try:
        forum_qs = __cursor.execute(get_forum_by_short_name_query, [short_name, ])
        if not __cursor.rowcount:
             __cursor.close()
             return HttpResponse(dumps({'code': codes.NOT_FOUND,
                                        'response': 'forum not found'}))
    except DatabaseError as db_err:
        __cursor.close() 
        return HttpResponse(dumps({'code': codes.UNKNOWN_ERR,
                                   'response': unicode(db_err)}))
    forum_id = __cursor.fetchone()[0]

    get_all_forum_users_specified_query = get_all_forum_users_query
    query_params = [forum_id, ]
    since_id = general_utils.validate_id(request.GET.get('since_id'))
    if since_id:
        get_all_forum_users_specified_query += '''AND id >= %s '''
        query_params.append(since_id)
    elif since_id == False and since_id is not None:
        __cursor.close()
        return HttpResponse(dumps({'code': codes.INCORRECT_QUERY,
                                   'response': 'since_id should be int'})) 
   
    order = request.GET.get('order', 'desc')
    if order.lower() not in ('asc', 'desc'):
        __cursor.close()
        return HttpResponse(dumps({'code': codes.INCORRECT_QUERY,
                                   'response': 'incorrect order parameter: {}'.format(order)}))
    
    get_all_forum_users_specified_query += '''ORDER BY user.name ''' + order

    limit = request.GET.get('limit')
    if limit:
        try:
            limit = int(limit)
        except ValueError:
             __cursor.close()
             return HttpResponse(dumps({'code': codes.INCORRECT_QUERY,
                                        'response': 'limit should be int'}))
        get_all_forum_users_specified_query += ''' LIMIT %s'''
        query_params.append(limit)

    try:
        users_qs = __cursor.execute(get_all_forum_users_specified_query, query_params) 
    except DatabaseError as db_err: 
        __cursor.close()
        return HttpResponse(dumps({'code': codes.UNKNOWN_ERR,
                                   'response': unicode(db_err)})) 
    users = []
    for user in __cursor.fetchall():
        users.append(get_user_by_id(user[0])[0])  
    __cursor.close()       
    return HttpResponse(dumps({'code': codes.OK,
                               'response': users
                               }))

