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

## CLOSE ##
select_thread_by_id_query = '''SELECT id FROM thread WHERE id = %s'''

close_thread_query = '''
                        UPDATE thread
                        SET isClosed = True
                        WHERE id = %s;
                     '''

@csrf_exempt 
def close_thread(request):
    __cursor = connection.cursor()
    try:
        json_request = loads(request.body) 
    except ValueError as value_err:
        __cursor.close()
        return HttpResponse(dumps({'code': codes.INVALID_QUERY,
                                   'response': unicode(value_err)}))
    
    try:
        thread_id = json_request['thread']
    except KeyError as key_err:
        __cursor.close()
        return HttpResponse(dumps({'code': codes.INCORRECT_QUERY,
                                   'response': 'Not found: {}'.format(unicode(key_err))}))    
   
    try:
        __cursor.execute(select_thread_by_id_query, [thread_id, ]) 
        if not __cursor.rowcount:
            __cursor.close()
            return HttpResponse(dumps({'code': codes.NOT_FOUND,
                                       'response': 'thread not found'}))
        __cursor.execute(close_thread_query, [thread_id, ])
    except DatabaseError as db_err: 
        __cursor.close()
        return HttpResponse(dumps({'code': codes.UNKNOWN_ERR,
                                   'response': unicode(db_err)}))

    __cursor.close() 
    return HttpResponse(dumps({'code': codes.OK,
                               'response': {
                                   'thread': thread_id
                                }})) 

## CREATE 
create_thread_query = '''INSERT INTO thread
                         (forum_id, title, isClosed, user_id, date, message, slug)
                         VALUES
                         (%s, %s, %s, %s, %s, %s, %s)
                      '''
select_last_id =      '''
                         SELECT LAST_INSERT_ID();
                      '''
update_thread_is_deleted_query = '''UPDATE thread
                                    SET isDeleted = %s
                                    WHERE id = %s
                                 '''

get_user_by_email_query = '''SELECT id FROM user
                             WHERE email = %s;
                          '''

get_forum_by_short_name_query = u'''SELECT forum.id
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
        forum = json_request['forum']
        title = json_request['title']
        is_closed = json_request['isClosed']
        email = json_request['user']
        date = json_request['date']
        message = json_request['message']
        slug = json_request['slug']
    except KeyError as key_err:
        __cursor.close()
        return HttpResponse(dumps({'code': codes.INCORRECT_QUERY,
                                   'response': 'Not found: {}'.format(unicode(key_err))}))    
   
    # validate user
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
    
    # validate forum
    try:
        __cursor.execute(get_forum_by_short_name_query, [forum, ])  
    except DatabaseError as db_err: 
        __cursor.close()
        return HttpResponse(dumps({'code': codes.UNKNOWN_ERR,
                                   'response': unicode(db_err)}))

    if not __cursor.rowcount:
        __cursor.close()
        return HttpResponse(dumps({'code': codes.NOT_FOUND,
                                   'response': 'forum not found'}))
    forum_id = __cursor.fetchone()[0]

    #validate date
    date = general_utils.validate_date(date)
    if not date:
        __cursor.close()
        return HttpResponse(dumps({'code': codes.INCORRECT_QUERY,
                                   'response': 'incorrect date fromat'}))
    #validate message
    if not message:
        __cursor.close()
        return HttpResponse(dumps({'code': codes.INCORRECT_QUERY,
                                   'response': 'message should not be empty'}))

    #validate slug
    if not slug:
        __cursor.close()
        return HttpResponse(dumps({'code': codes.INCORRECT_QUERY,
                                   'response': 'slug should not be empty'}))
    #validate slug
    if not title:
        __cursor.close()
        return HttpResponse(dumps({'code': codes.INCORRECT_QUERY,
                                   'response': 'title should not be empty'}))

    #validate is_closed
    is_closed = bool(is_closed)
    try:
        __cursor.execute(create_thread_query, [forum_id, title, is_closed, 
                                               user_id, date, message, slug])
        __cursor.execute(select_last_id, [])
    except DatabaseError as db_err: 
        __cursor.close()
        return HttpResponse(dumps({'code': codes.UNKNOWN_ERR,
                                   'response': unicode(db_err)})) 
    thread_id = __cursor.fetchone()[0]

    is_deleted = json_request.get('isDeleted')
    if is_deleted is not None:
        is_deleted = bool(is_deleted)
        try:
            __cursor.execute(update_thread_is_deleted_query, [is_deleted, thread_id])
        except DatabaseError as db_err: 
            __cursor.close()
            return HttpResponse(dumps({'code': codes.UNKNOWN_ERR,
                                       'response': unicode(db_err)})) 
    else:
        is_deleted = False       
    __cursor.close()
    return HttpResponse(dumps({'code': codes.OK,
                               'response': {
                                   "date": date,
                                   "forum": forum,
                                    "id": thread_id,
                                    "isClosed": is_closed,
                                    "isDeleted": is_deleted,
                                    "message": message,
                                    "slug": slug,
                                    "title": title,
                                    "user": email
                                }}))
                                

## DETAILS
def details(request):
    __cursor = connection.cursor()
    if request.method != 'GET':
        __cursor.close()
        return HttpResponse(dumps({'code': codes.INVALID_QUERY,
                                   'response': 'request method should be GET'}))
    thread_id = general_utils.validate_id(request.GET.get('thread'))
    if thread_id is None:
        __cursor.close()
        return HttpResponse(dumps({'code': codes.INVALID_QUERY,
                                   'response': 'thread id not found'})) 
    if thread_id == False:
        __cursor.close()
        return HttpResponse(dumps({'code': codes.INVALID_QUERY,
                                   'response': 'thread id should be int'})) 
    try:
        thread, related_ids = get_thread_by_id(__cursor, thread_id) 
    except DatabaseError as db_err: 
        __cursor.close()
        return HttpResponse(dumps({'code': codes.UNKNOWN_ERR,
                                   'response': unicode(db_err)}))
    except TypeError:
        __cursor.close()
        return HttpResponse(dumps({'code': codes.INCORRECT_QUERY,
                                   'response': 'thread doesn\'t exist'}))

    related = request.GET.getlist('related')
    for related_ in filter(lambda x: x in related_functions_dict.keys(), related):
        if related_ != 'thread':
             get_related_info_func = related_functions_dict[related_]
             thread[related_], related_ids_ = get_related_info_func(__cursor, related_ids[related_]) 
    __cursor.close()        
    return HttpResponse(dumps({'code': codes.OK,
                               'response': thread}))

## List threads
get_all_threads_query = '''SELECT thread.date, thread.dislikes, forum.short_name,
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
                                 WHERE thread.{}_id = %s
                            '''

get_user_id_by_email = '''SELECT id FROM  user
                          WHERE email = %s'''

get_forum_id_by_short_name = '''SELECT id FROM forum
                                WHERE short_name = %s'''

def list_threads(request):
    __cursor = connection.cursor()
    if request.method != 'GET':
        __cursor.close()
        return HttpResponse(dumps({'code': codes.INVALID_QUERY,
                                   'response': 'request method should be GET'}))
    short_name = request.GET.get('forum')
    email = request.GET.get('user')
    if short_name is None and email is None:
        __cursor.close()
        return HttpResponse(dumps({'code': codes.INVALID_QUERY,
                                   'response': 'thread id or forum id not found'})) 
    if short_name and email:
        __cursor.close()
        return HttpResponse(dumps({'code': codes.INVALID_QUERY,
                                   'response': 'you should specify thread OR forum'}))
    if email:
        related_table_name = 'user'
        related_query = get_user_id_by_email 
        related_params = [email, ]
    else:
        related_table_name = 'forum'
        related_query = get_forum_id_by_short_name 
        related_params = [short_name, ]     
    try:
        id_qs = __cursor.execute(related_query, related_params)
        if not __cursor.rowcount:
            __cursor.close()
            return HttpResponse(dumps({'code': codes.NOT_FOUND,
                                       'response': '{} not found'.format(related_table_name)})) 
    except DatabaseError as db_err: 
        __cursor.close()
        return HttpResponse(dumps({'code': codes.UNKNOWN_ERR,
                                   'response': unicode(db_err)}))
    related_id = id_qs[0]
    query_params = [related_id, ]
    get_thread_list_specified_query = get_all_threads_query
    since_date = general_utils.validate_date(request.GET.get('since'))
    if since_date:
        get_thread_list_specified_query += '''AND post.date >= %s '''
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
    
    get_thread_list_specified_query += '''ORDER BY thread.date ''' + order

    limit = request.GET.get('limit')
    if limit:
        try:
            limit = int(limit)
        except ValueError:
            __cursor.close()
            return HttpResponse(dumps({'code': codes.INCORRECT_QUERY,
                                       'response': 'limit should be int'}))
        get_thread_list_specified_query += ''' LIMIT %s'''
        query_params.append(limit)

    try:
        threads_qs = __cursor.execute(get_thread_list_specified_query.format(related_table_name), 
                                          query_params)
    except DatabaseError as db_err: 
        __cursor.close()
        return HttpResponse(dumps({'code': codes.UNKNOWN_ERR,
                                   'response': unicode(db_err)})) 
    
    threads = []
    for thread in __cursor.fetchall():
        threads.append({
            "date": thread[0].strftime("%Y-%m-%d %H:%M:%S") ,
            "dislikes": thread[1],
            "forum": thread[2],
            "id": thread[3],
            "isClosed": not not thread[4],
            "isDeleted": not not thread[5],
            "likes": thread[6],
            "message": thread[7],
            "points": thread[8],
            "posts": thread[9], 
            "slug": thread[10],
            "title": thread[11],
            "user": thread[12]
            })
    __cursor.close()
    return HttpResponse(dumps({'code': codes.OK,
                               'response': threads}))

 
## LIST POSTS ##
get_all_thread_posts_query = '''SELECT post.date, post.dislikes, forum.short_name,
                                      post.id, post.isApproved, post.isDeleted, post.isEdited,
                                      post.isHighlighted, post.isSpam, post.likes, post.message, post.parent,
                                      post.likes - post.dislikes as points, post.thread_id, user.email,
                                      forum.id, thread.id, user.id,
                                      post.hierarchy_id
                                FROM post INNER JOIN forum ON post.forum_id = forum.id
                                INNER JOIN user ON user.id = post.user_id
                                WHERE post.thread_id = %s
                            '''

get_thread_posts_number = '''SELECT head_posts_number
                             FROM post_hierarchy_utils
                             WHERE thread_id = %s;  
                          '''
def listPosts(request):
    __cursor = connection.cursor()
    if request.method != 'GET':
        __cursor.close()
        return HttpResponse(dumps({'code': codes.INVALID_QUERY,
                                   'response': 'request method should be GET'}))
    thread = request.GET.get('thread')
    thread_id = general_utils.validate_id(thread)
    if thread_id is None:
        __cursor.close()
        return HttpResponse(dumps({'code': codes.INVALID_QUERY,
                                   'response': 'thread id is required'}))
    if thread_id == False:
        __cursor.close()
        return HttpResponse(dumps({'code': codes.INVALID_QUERY,
                                   'response': 'thread id should be int'}))
    try:
       thread_id_qs = __cursor.execute(get_thread_id_by_id, [thread_id,]) 
    except DatabaseError as db_err:
        __cursor.close() 
        return HttpResponse(dumps({'code': codes.UNKNOWN_ERR,
                                   'response': unicode(db_err)}))
    if not __cursor.rowcount:
        __cursor.close()
        return HttpResponse(dumps({'code': codes.INVALID_QUERY,
                                   'response': 'thread was not found'})) 
    thread_id = __cursor.fetchone()[0] 

    get_all_posts_specified_posts_query = get_all_thread_posts_query
    query_params = [thread_id, ]
    since_date = general_utils.validate_date(request.GET.get('since'))
    if since_date:
        get_all_posts_specified_query += '''AND post.date >= %s '''
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
    
    get_all_posts_query_postfix = '''ORDER BY post.{} ''' + order

    sort = request.GET.get('sort', 'flat')
    if sort.lower() not in ('flat', 'tree', 'parent_tree'):
        __cursor.close()
        return HttpResponse(dumps({'code': codes.INCORRECT_QUERY,
                                   'response': 'incorrect sort parameter: {}'.format(sort)}))

    if sort == 'flat':
        get_all_posts_query_postfix = get_all_posts_query_postfix.format('date')
    else:
        get_all_posts_query_postfix = get_all_posts_query_postfix.format('hierarchy_id')

    limit = request.GET.get('limit')
    if limit:
        try:
            limit = int(limit)
        except ValueError:
             __cursor.close()
             return HttpResponse(dumps({'code': codes.INCORRECT_QUERY,
                                        'response': 'limit should be int'}))
        if sort == 'flat' or sort == 'tree':
            get_all_posts_specified_query += get_all_posts_query_postfix + ''' LIMIT %s'''
            query_params.append(limit)
        else:
            if order == 'asc':
                operation = '<='
            else:
                operation = '>='
                try:
                    max_posts_number_qs = __cursor.execute(get_thread_posts_number, [thread_id,]) 
                except DatabaseError as db_err: 
                    __cursor.close()
                    return HttpResponse(dumps({'code': codes.UNKNOWN_ERR,
                                                'response': unicode(db_err)}))
                if __cursor.rowcount:
                    max_posts_number = __cursor.fetchone()[0]
                else:
                    max_posts_number = 0     
                limit = max_posts_number - limit + 1
                if limit < 1:
                    limit = 1
            get_all_posts_specified_query += "AND SUBSTR(post.hierarchy_id, 1, 1) {} '{}'".format(operation, limit) + \
                                              get_all_posts_query_postfix

    try:
        posts_qs = __cursor.execute(get_all_posts_specified_query, query_params) 
    except DatabaseError as db_err: 
        __cursor.close()
        return HttpResponse(dumps({'code': codes.UNKNOWN_ERR,
                                   'response': unicode(db_err)})) 
    
    posts = []
    for post in __cursor.fetchall():
        posts.append({
            "date": post[0].strftime("%Y-%m-%d %H:%M:%S") ,
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
    __cursor.close()
    return HttpResponse(dumps({'code': codes.OK,
                               'response': posts
                               }))

## OPEN
open_thread_by_id_query = '''UPDATE thread
                             SET isClosed = False
                             WHERE id = %s;
                          ''' 
@csrf_exempt
def open_thread(request):
    __cursor = connection.cursor()
    try:
        json_request = loads(request.body) 
    except ValueError as value_err:
        __cursor.close()
        return HttpResponse(dumps({'code': codes.INVALID_QUERY,
                                   'response': unicode(value_err)}))
    
    try:
        thread_id = json_request['thread']
    except KeyError as key_err:
        __cursor.close()
        return HttpResponse(dumps({'code': codes.INCORRECT_QUERY,
                                   'response': 'Not found: {}'.format(unicode(key_err))}))    
   
    try:
        __cursor.execute(select_thread_by_id_query, [thread_id, ]) 
        if not __cursor.rowcount:
            __cursor.close()
            return HttpResponse(dumps({'code': codes.NOT_FOUND,
                                       'response': 'thread not found'}))
        thread_id_qs = __cursor.execute(select_and_open_thread_by_id_query, [thread_id, ])  
    except DatabaseError as db_err: 
        __cursor.close()
        return HttpResponse(dumps({'code': codes.UNKNOWN_ERR,
                                   'response': unicode(db_err)}))
    __cursor.close() 
    return HttpResponse(dumps({'code': codes.OK,
                               'response': {
                                   'thread': thread_id
                                }})) 

## REMOVE
remove_thread_by_id_query = '''UPDATE thread
                               SET isDeleted = True
                               WHERE id = %s;
                            ''' 

@csrf_exempt
def remove(request):
    __cursor = connection.cursor()
    try:
        json_request = loads(request.body) 
    except ValueError as value_err:
        __cursor.close()
        return HttpResponse(dumps({'code': codes.INVALID_QUERY,
                                   'response': unicode(value_err)}))
    
    try:
        thread_id = json_request['thread']
    except KeyError as key_err:
        __cursor.close()
        return HttpResponse(dumps({'code': codes.INCORRECT_QUERY,
                                   'response': 'Not found: {}'.format(unicode(key_err))}))    
    try:
        __cursor.execute(select_thread_by_id_query, [thread_id, ]) 
        if not __cursor.rowcount:
            __cursor.close()
            return HttpResponse(dumps({'code': codes.NOT_FOUND,
                                       'response': 'thread not found'}))
        __cursor.execute(remove_thread_by_id_query, [thread_id, ])  
    except DatabaseError as db_err: 
        __cursor.close()
        return HttpResponse(dumps({'code': codes.UNKNOWN_ERR,
                                   'response': unicode(db_err)}))
    __cursor.close() 
    return HttpResponse(dumps({'code': codes.OK,
                               'response': {
                                   'thread': thread_id
                                }})) 

## RESTORE
restore_thread_by_id_query = '''UPDATE thread
                                SET isDeleted = False
                                WHERE id = %s;
                             ''' 
@csrf_exempt
def restore(request):
    __cursor = connection.cursor()
    try:
        json_request = loads(request.body) 
    except ValueError as value_err:
        __cursor.close()
        return HttpResponse(dumps({'code': codes.INVALID_QUERY,
                                   'response': unicode(value_err)}))
    
    try:
        thread_id = json_request['thread']
    except KeyError as key_err:
        __cursor.close()
        return HttpResponse(dumps({'code': codes.INCORRECT_QUERY,
                                   'response': 'Not found: {}'.format(unicode(key_err))}))    
   
    try:
        __cursor.execute(select_thread_by_id_query, [thread_id, ]) 
        if not __cursor.rowcount:
            __cursor.close()
            return HttpResponse(dumps({'code': codes.NOT_FOUND,
                                       'response': 'thread not found'}))
        __cursor.execute(restore_thread_by_id_query, [thread_id, ]) 
    except DatabaseError as db_err: 
        __cursor.close()
        return HttpResponse(dumps({'code': codes.UNKNOWN_ERR,
                                   'response': unicode(db_err)}))
    __cursor.close() 
    return HttpResponse(dumps({'code': codes.OK,
                               'response': {
                                   'thread': thread_id
                                }})) 


## SUBSCRIBE
create_subscription_query = '''INSERT INTO subscriptions
                               (user_id, thread_id)
                               VALUES
                               (%s, %s)
                            '''

@csrf_exempt
def subscribe(request):
    __cursor = connection.cursor()
    try:
        json_request = loads(request.body) 
    except ValueError as value_err:
        __cursor.close()
        return HttpResponse(dumps({'code': codes.INVALID_QUERY,
                                   'response': str(value_err)}))
    
    try:
        email = unicode(json_request['user'])
        thread = json_request['thread']
    except KeyError as key_err:
        __cursor.close()
        return HttpResponse(dumps({'code': codes.INCORRECT_QUERY,
                                   'response': 'Not found: {}'.format(str(key_err))}))  

    # validate user
    try:
        user_id_qs = __cursor.execute(get_user_by_email_query, [email, ])
    except DatabaseError as db_err:
        __cursor.close() 
        return HttpResponse(dumps({'code': codes.UNKNOWN_ERR,
                                       'response': unicode(db_err)}))
    if not __cursor.rowcount:
        __cursor.close()
        return HttpResponse(dumps({'code': codes.NOT_FOUND,
                                    'response': 'user with not found'}))
    user_id = __cursor.fetchone()[0]

    #validate thread
    thread_id = general_utils.validate_id(thread)
    if thread_id == False:
        __cursor.close()
        return HttpResponse(dumps({'code': codes.INVALID_QUERY,
                                   'response': 'thread id should be int'}))
    try:
       thread_id_qs = __cursor.execute(get_thread_id_by_id, [thread_id,]) 
    except DatabaseError as db_err: 
        __cursor.close()
        return HttpResponse(dumps({'code': codes.UNKNOWN_ERR,
                                   'response': unicode(db_err)}))
    if not __cursor.rowcount:
        __cursor.close()
        return HttpResponse(dumps({'code': codes.INVALID_QUERY,
                                   'response': 'thread was not found'})) 
    thread_id = __cursor.fetchone()[0]  
      
    try:
        __cursor.execute(create_subscription_query, user_id, thread_id)  
    except IntegrityError:
        pass
    except DatabaseError as db_err: 
        __cursor.close()
        return HttpResponse(dumps({'code': codes.UNKNOWN_ERR,
                                   'response': unicode(db_err)}))  
    __cursor.close()
    return HttpResponse(dumps({'code': codes.OK,
                               'response': {"thread": thread_id,
                                            "user": email}}))

## UNSUBSCRIBE
delete_subscription_query = '''DELETE FROM subscriptions
                               WHERE thread_id = %s
                               AND user_id = %S
                            '''

@csrf_exempt
def unsubscribe(request):
    __cursor = connection.cursor()
    try:
        json_request = loads(request.body) 
    except ValueError as value_err:
        __cursor.close()
        return HttpResponse(dumps({'code': codes.INVALID_QUERY,
                                   'response': str(value_err)}))
    
    try:
        email = unicode(json_request['user'])
        thread = json_request['thread']
    except KeyError as key_err:
        __cursor.close()
        return HttpResponse(dumps({'code': codes.INCORRECT_QUERY,
                                   'response': 'Not found: {}'.format(str(key_err))}))  

    # validate user
    try:
        user_id_qs = __cursor.execute(get_user_by_email_query, [email, ]) 
    except DatabaseError as db_err: 
        __cursor.close()
        return HttpResponse(dumps({'code': codes.UNKNOWN_ERR,
                                       'response': unicode(db_err)}))
    if not __cursor.rowcount:
        __cursor.close()
        return HttpResponse(dumps({'code': codes.NOT_FOUND,
                                    'response': 'user with not found'}))
    user_id = __cursor.fetchone()[0]

    #validate thread
    thread_id = general_utils.validate_id(thread)
    if thread_id == False:
        __cursor.close()
        return HttpResponse(dumps({'code': codes.INVALID_QUERY,
                                   'response': 'thread id should be int'}))
    try:
       thread_id_qs = __cursor.execute(get_thread_id_by_id, [thread_id,]).fetchone() 
    except DatabaseError as db_err: 
        __cursor.close()
        return HttpResponse(dumps({'code': codes.UNKNOWN_ERR,
                                   'response': unicode(db_err)}))
    if not __cursor.rowcount:
        __cursor.close()
        return HttpResponse(dumps({'code': codes.INVALID_QUERY,
                                   'response': 'thread was not found'}))
    thread_id = __cursor.fetchone()[0]  
      
    try:
        __cursor.execute(delete_subscription_query, [thread_id, user_id])  
    except DatabaseError as db_err: 
        __cursor.close()
        return HttpResponse(dumps({'code': codes.UNKNOWN_ERR,
                                   'response': unicode(db_err)}))  
    __cursor.close()
    return HttpResponse(dumps({'code': codes.OK,
                               'response': {"thread": thread_id,
                                            "user": email}}))


## UPDATE ##
update_thread_message_query = u'''UPDATE thread
                                  SET message = %s,
                                    slug = %s,
                                  WHERE id = %s;
                               '''


@csrf_exempt
def update(request):
    __cursor = connection.cursor()
    try:
        json_request = loads(request.body) 
    except ValueError as value_err:
        __cursor.close()
        return HttpResponse(dumps({'code': codes.INVALID_QUERY,
                                   'response': unicode(value_err)}))   
    try:
        thread_id = json_request['thread']
        message = unicode(json_request['message'])
        slug = unicode(json_request['slug'])
    except KeyError as key_err:
        __cursor.close()
        return HttpResponse(dumps({'code': codes.INCORRECT_QUERY,
                                   'response': 'Not found: {}'.format(unicode(key_err))}))

    thread_id = general_utils.validate_id(thread_id) 
    if thread_id == False:
        __cursor.close()
        return HttpResponse(dumps({'code': codes.INVALID_QUERY,
                                   'response': 'thread id should be int'})) 
    try:
        __cursor.execute(select_thread_by_id_query, [thread_id, ]) 
        if not __cursor.rowcount:
            __cursor.close()
            return HttpResponse(dumps({'code': codes.NOT_FOUND,
                                       'response': 'thread not found'}))
        thread_id_qs = __cursor.execute(update_thread_message_query, 
                                        [message, slug, thread_id, ]) 
        thread, related_obj = get_thread_by_id(__cursor, thread_id)
    except DatabaseError as db_err:
        __cursor.close() 
        return HttpResponse(dumps({'code': codes.UNKNOWN_ERR,
                                   'response': unicode(db_err)})) 
    __cursor.close()
    return HttpResponse(dumps({'code': codes.OK,
                               'response': thread}))

## VOTE ##
update_thread_votes_request = '''UPDATE thread
                                 SET {} = {} + 1
                                 WHERE id = %s;
                            '''

@csrf_exempt
def vote(request):
    __cursor = connection.cursor()
    try:
        json_request = loads(request.body) 
    except ValueError as value_err:
        __cursor.close()
        return HttpResponse(dumps({'code': codes.INVALID_QUERY,
                                   'response': unicode(value_err)}))   
    try:
        thread_id = json_request['thread']
        vote = json_request['vote']
    except KeyError as key_err:
        __cursor.close()
        return HttpResponse(dumps({'code': codes.INCORRECT_QUERY,
                                   'response': 'Not found: {}'.format(unicode(key_err))}))

    thread_id = general_utils.validate_id(thread_id) 
    if thread_id == False:
        __cursor.close()
        return HttpResponse(dumps({'code': codes.INVALID_QUERY,
                                   'response': 'post id should be int'}))
    try:
        vote = int(vote)
        if abs(vote) != 1:
            raise ValueError
    except ValueError:
        __cursor.close()
        return HttpResponse(dumps({'code': codes.INCORRECT_QUERY,
                                   'response': 'incorrect vote value'})) 
    if vote < 0:
        column_name = 'dislikes'
    else:
        column_name = 'likes'
  
    try:
        __cursor.execute(select_thread_by_id_query, [thread_id, ]) 
        if not __cursor.rowcount:
            __cursor.close()
            return HttpResponse(dumps({'code': codes.NOT_FOUND,
                                       'response': 'thread not found'}))
        thread_id_qs = __cursor.execute(update_thread_votes_request.format(column_name), [thread_id, ])
        thread, related_obj = get_thread_by_id(__cursor, thread_id)
    except DatabaseError as db_err:
        __cursor.close() 
        return HttpResponse(dumps({'code': codes.UNKNOWN_ERR,
                                   'response': unicode(db_err)}))     
    __cursor.close()
    return HttpResponse(dumps({'code': codes.OK,
                               'response': thread}))
