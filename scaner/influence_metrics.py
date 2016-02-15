import pyorient
import math
import numpy as np
# from scipy.sparse import csr_matrix
# from scipy.sparse import lil_matrix
import gc

# FALTA TENER EL NÚMERO TOTAL DE TWEETS DE UN USUARIO FUERA DE LA BUSQUEDA
# Metodo para calcular la metrica TR SCORE de todos los usuarios
def user_tweetrate_score(userlist):
    for user in userlist:
        tweets_related_user = client.query("select from Tweet where userid = '" + str(user.oRecordData['userid']) + "'")
        tweets_related_user = len(tweets_related_user)
        tweets_total_user = int(user.oRecordData['total_tweets'])
        TR_score = tweets_related_user/tweets_total_user
        command = "update (select from User where userid = '" + str(user.oRecordData['userid']) +"') set TR_score = '" + str(TR_score) + "'"
        command = "update (select from User where userid = '" + str(user.oRecordData['userid']) + "') set TR_score = '" + str(0.5) + "'"
        client.command(command)


# Metodo para calcular la metrica UI SCORE
def influence_score(number_of_users, number_of_tweets):
    # Parametros
    limit = 10000
    iterationRID = "#-1:-1"
    index = 0
    # iterations = max([(number_of_users/limit), (number_of_tweets/limit)])
    iterations = math.ceil(number_of_tweets/limit)
    print("numero de iteraciones: " + str(iterations))

    # Creamos las matrices At, Ar y As vacia
    At = lil_matrix((number_of_tweets,number_of_users))
    Ar = lil_matrix((number_of_users,number_of_tweets))
    As = lil_matrix((number_of_users,number_of_tweets))

    userlist = client.query("select from User order by followers desc limit 500")

    for iteration_num in range(0,iterations):
        tweetlist = client.query("select from Tweet where @rid > " + iterationRID + " limit "+ str(limit))

        # Iteramos los usuarios y los tweets para rellenar las matrices
        index_start = index
        for n,user in enumerate(userlist):

            # Creamos el vector para la matriz At
            user_tweet_At = np.array([])
            # Creamos el vector para la matriz Ar
            tweet_user_Ar = np.array([])
            # Creamos el vector para la matriz As (FALTA PARAMETRO s)
            user_user_As = np.array([])


            # PUEDO OPTIMIZAR METIENDO ESTAS QUERYS EN LOS IF DE DEBAJO
            user_created = client.query("select expand(in('Created_by')) from (select from User where userid = '" + str(user.oRecordData['userid']) + "')")
            user_retweeted = client.query("select expand(in('Retweeted_by')) from (select from User where userid = '" + str(user.oRecordData['userid']) + "')")
            # user_replied = client.query("select expand(in('Replied_by')) from (select from User where userid = '" + user.oRecordData['userid'] + "')")
            user_follows_created = client.query("select expand(out('Follows').in('Created_by')) from (select from User where userid = '" + str(user.oRecordData['userid']) + "')")
            user_follows_retweeted = client.query("select expand(out('Follows').in('Retweeted_by')) from (select from User where userid = '" + str(user.oRecordData['userid']) + "')")        

            for tweet in tweetlist:
                found_At = False
                found_Ar = False
                found_As = False

                # Calculamos el vector para At y para Ar
                for retweeted in user_retweeted:
                    if retweeted.oRecordData['tid'] == tweet.oRecordData['tid']:
                        user_tweet_At = np.append(user_tweet_At, np.ones(1))
                        found_At = True
                        tweet_user_Ar = np.append(tweet_user_Ar, np.ones(1))
                        found_Ar = True
                        break

                if not found_At:        
                    for created in user_created:
                        if created.oRecordData['tid'] == tweet.oRecordData['tid']:
                            user_tweet_At = np.append(user_tweet_At, np.ones(1))
                            found_At = True
                            break

                # if not found_Ar:
                #     for replied in user_replied:
                #         if replied.oRecordData['tid'] == tweet.oRecordData['tid']:
                #             tweet_user_Ar = np.append(tweet_user_Ar, np.ones(1))
                #             found_Ar = True
                #             break 

                # Calculamos el vector para As
                for tweet_follow in user_follows_created:
                    if tweet_follow.oRecordData['tid'] == tweet.oRecordData['tid']:
                        user_user_As = np.append(user_user_As, np.ones(1))
                        found_As = True
                        break
                if not found_As:
                    for retweet_follow in user_follows_retweeted:
                        if tweet_follow.oRecordData['tid'] == tweet.oRecordData['tid']:
                            user_user_As = np.append(user_user_As, np.ones(1))
                            found_As = True
                            break

                if not found_As:
                    user_user_As = np.append(user_user_As,np.zeros(1))
                if not found_At:
                    user_tweet_At = np.append(user_tweet_At, np.zeros(1))
                if not found_Ar:
                    tweet_user_Ar = np.append(tweet_user_Ar,np.zeros(1))

            # At[index_start:index,n] = user_tweet_At
            # Ar[n,index_start:index] = tweet_user_Ar
            # As[n,index_start:index] = user_user_As

            arrayindex = index_start

            if arrayindex < (number_of_tweets-(limit+5000)):
                for element in user_tweet_At:                
                    At[arrayindex,n] = element
                    arrayindex +=1
                arrayindex = index_start
                for element in tweet_user_Ar:                
                    Ar[n,arrayindex] = element
                    arrayindex +=1
                arrayindex = index_start
                for element in user_user_As:
                    As[n,arrayindex] = element
                    arrayindex +=1
            else:
                for element in user_tweet_At:                
                    At[arrayindex,n] = element
                    arrayindex +=1
                    if arrayindex > number_of_tweets:
                        break
                arrayindex = index_start
                for element in tweet_user_Ar:                
                    Ar[n,arrayindex] = element
                    arrayindex +=1
                    if arrayindex > number_of_tweets:
                        break
                arrayindex = index_start
                for element in user_user_As:
                    As[n,arrayindex] = element
                    arrayindex +=1
                    if arrayindex > number_of_tweets:
                        break


        #CONSEGUIR OBTENER RID
        index += 10000 
        iterationRID = tweet._rid
        print("Fin de iteracion " + str(iteration_num))

    # DAMPING FACTOR
    d = 0.5

    Ar = csr_matrix(Ar)
    At = csr_matrix(At)
    As = csr_matrix(As)

    # Creamos la matriz Bt:
    Bt = lil_matrix((number_of_tweets,number_of_users))
    n_filas_At = At.shape[0]
    n_columnas_At = At.shape[1]
    for i in range(0, n_filas_At):
        sumatorio_At = At[i].sum()
        if sumatorio_At != 0:
            for j in range(0,n_columnas_At):
                Bt[i,j] = At[i,j]/sumatorio_At
        else:
            for j in range(0,n_columnas_At):
                Bt[i,j] = 0

    Bt = csr_matrix(Bt)

    # LIMPIAMOS MEMORIA
    At = 0
    gc.collect()



    # Creamos la matriz Ba
    Ba = lil_matrix((number_of_users,number_of_tweets))
    n_filas_Ar = Ar.shape[0]
    n_columnas_Ar = Ar.shape[1]

    for i in range(0, n_filas_Ar):
        sumatorio_Ar = Ar[i].sum()
        sumatorio_As = As[i].sum()
        if sumatorio_As != 0:
            if sumatorio_Ar == 0:
                for j in range(0,n_columnas_Ar):
                    Ba[i,j] = As[i,j]/sumatorio_As
            else:
                for j in range(0,n_columnas_Ar):
                    Ba[i,j] = (Ar[i,j]/sumatorio_Ar)*(1-d) + (As[i,j]/sumatorio_As)*d
        else:
            Ba[i,j] = 0
        
    Ba = csr_matrix(Ba)

    # LIMPIAMOS MEMORIA
    Ar = 0
    As = 0
    gc.collect()

    # Calculamos UI y TI
    users_vector = np.ones((number_of_users))/number_of_users
    tweets_vector =  np.ones((number_of_tweets))/number_of_tweets

    Ba_transpose = Ba.transpose()
    Bt_transpose = Bt.transpose()

    # LIMPIAMOS MEMORIA
    Ba = 0
    Bt = 0
    gc.collect()

    for k in range(1, 10000):
        tweets_vector = Ba_transpose.dot(users_vector)
        users_vector = Bt_transpose.dot(tweets_vector)


    # LIMPIAMOS MEMORIA
    Ba_transpose = 0
    Bt_transpose = 0
    gc.collect()


    # Normalizamos UI
    UI_vector = users_vector/np.amax(users_vector)

    # ALMACENAMOS EN LA DB LAS PUNTUACIONES
    for n,user in enumerate(userlist):
        command = "update (select from User where userid = '" + str(user.oRecordData['userid']) + "') set UI_score = '" + str(UI_vector[n]) + "', UI_unnormalized = '" + str(users_vector[n]) + "'"
        client.command(command)

    newindex = 0
    iterationRID = "#-1:-1"
    for iteration_num in range(0,iterations):
        tweetlist = client.query("select from Tweet where @rid > " + iterationRID + " limit "+ str(limit))

        for n,tweet in enumerate(tweetlist):
            command = "update (select from Tweet where tid = '" + str(tweet.oRecordData['tid']) + "') set TI_score = '" + str(tweets_vector[n+newindex]) + "'"
            client.command(command)
        newindex += 10000 
        iterationRID = tweet._rid

    # while (error_u > 0.1) or (error_t > 0.1):
    #     error_u = -np.mod(users_vector)
    #     error_t = -np.mod(tweets_vector)
    #     tweets_vector = np.dot(Ba.transpose(), users_vector)
    #     users_vector = np.dot(Bt.transpose(), tweets_vector)
    #     error_u += np.mod(users_vector)
    #     error_t += np.mod(tweets_vector)

    
def follow_relation_factor_user(number_of_users):

    userlist = client.query("select from User order by followers desc limit 500")

    Af = np.zeros((number_of_users, number_of_users))

    for n, user in enumerate(userlist):
        user_user_Af = np.array([])

        user_follows = client.query("select expand(out('Follows')) from (select from User where userid = '" + str(user.oRecordData['userid']) + "')")
        
        for user_2 in userlist:
            found_Af = False

            for follow in user_follows:
                if (user_2.oRecordData['userid'] == follow.oRecordData['userid']):
                    user_user_Af = np.append(user_user_Af, np.ones(1))
                    found_Af = True
                    break
            if not found_Af:
                user_user_Af = np.append(user_user_Af,np.zeros(1))

        Af[n,:] = user_user_Af

    # DAMPING FACTOR
    d = 0.5

    # Creamos la matriz de adyacencia Bf
    Bf = np.zeros((number_of_users, number_of_users))
    n_users = Af.shape[0]
    for n in range(0, n_users):
        sumatorio_Af = Af[n].sum()
        Bf_row = np.ones(n_users)
        if sumatorio_Af == 0:
            Bf_row = Bf_row/n_users
        else:
            Bf_row = (Af[n]/sumatorio_Af)*(1-d) + d/n_users

        Bf[n,:] = Bf_row

    # Calculamos FR
    follow_vector = np.ones((number_of_users))/number_of_users
    
    for k in range(1, 500):
        follow_vector = np.dot(Bf.transpose(), follow_vector)

    # Normalizamos FR
    FR_vector = follow_vector/np.amax(follow_vector)

    # Metemos los resultados en la DB
    for n,user in enumerate(userlist):
        command = "update (select from User where userid = '" + str(user.oRecordData['userid']) +"') set FR_score = '" + str(FR_vector[n]) + "'"
        client.command(command)


# Metodo para calcular la relevancia de un usuario a partir de las otras métricas
def user_relevance_score():
    userlist = client.query("select from User order by followers desc limit 500")
    # Pesos para el ajuste de las diferentes métricas: wr + wi + wf = 1
    wr = 0.1
    wi = 0.4
    wf = 0.5
    for user in userlist:
        # print ("Puntuación TR de user " + str(userid) + " = " + user[0].oRecordData['TR_score'])
        # print ("Puntuación UI de user " + str(userid) + " = " + user[0].oRecordData['UI_score'])
        # print ("Puntuación FR de user " + str(userid) + " = " + user[0].oRecordData['FR_score'])
        user_relevance = float(user.oRecordData['TR_score'])**wr + float(user.oRecordData['UI_score'])**wi + float(user.oRecordData['FR_score'])**wf
        print ("Relevancia de user " + str(user.oRecordData['userid']) + " = " + str(user_relevance))
        command = "update (select from User where userid = '" + str(user.oRecordData['userid']) +"') set user_relevance = '" + str(user_relevance) + "'"
        client.command(command)

# Metodo para conseguir la lista de usuarios ordenados por su relevacia
def user_ranking():
    ranking = client.query("select from User order by user_relevance desc limit 100")
    for n, user in enumerate(ranking):
        print ("En el puesto número " + str(n+1) + " tenemos al usuario " + str(user.oRecordData['userid']))

# Metodo para conseguir la lista de tweets ordenados por su relevacia
def tweet_ranking():
    ranking = client.query("select from Tweet order by tweet_relevance desc limit 100")
    for n, tweet in enumerate(ranking):
        print ("En el puesto número " + str(n+1) + " tenemos el tweet " + str(tweet.oRecordData['tid']))


# Metodo para calcular el parametro IMPACT de un usuario
def impact_user(number_of_tweets):
    userlist = client.query("select from User order by followers desc limit 500")
    impact_vector = np.array([])
    # DAMPING FACTOR
    d = 0.5
    # SMOOTHING PARAMETER
    sigma = 0.5

    for n, user in enumerate(userlist):
        # tweets_replied = client.query("select expand(in('Replied_by')) from (select from User where userid = '" + user.oRecordData['userid'] + "')")
        tweets_retweeted = client.query("select expand(in('Retweeted_by')) from (select from User where userid = '" + str(user.oRecordData['userid']) + "')")
        n_tweets_related = len(tweets_retweeted) # + len(tweets_replied)
        if n_tweets_related == 0:
            user_impact = float(user.oRecordData['UI_unnormalized'])/number_of_tweets
        else:
            user_impact = ((float(user.oRecordData['UI_unnormalized'])/(n_tweets_related+sigma))*(1-d)) + ((float(user.oRecordData['UI_unnormalized'])/number_of_tweets)*d)
        
        command = "update (select from User where userid = '" + str(user.oRecordData['userid']) +"') set impact = '" + str(user_impact) + "'"
        client.command(command)



# Metodo para calcular el parametro VOICE de los usuario (As-is)
def voice_user():
    userlist = client.query("select from User order by followers desc limit 500")
    # Parametro SIGMA de suavizado
    sigma = 0.5
    # Calculamos VOICE para cada usuario
    for n, user in enumerate(userlist):
        tweets_user = client.query("select expand(in('Created_by')) from (select from User where userid = '" + str(user.oRecordData['userid']) + "')")
        retweets_user = client.query("select expand(in('Retweeted_by')) from (select from User where userid = '" + str(user.oRecordData['userid']) + "')")
        sumatorio_tweet_TI = 0
        sumatorio_retweet_TI = 0
        for tweet in tweets_user:
            try:
                sumatorio_tweet_TI += float(tweet.oRecordData['TI_score'])
            except:
                pass
        for retweet in retweets_user:
            try:
                sumatorio_retweet_TI += float(retweet.oRecordData['TI_score'])
            except:
                pass

        retweets_user = client.query("select expand(in('Retweeted_by')) from (select from User where userid = '" + str(user.oRecordData['userid']) + "')")
        voice_t = (1/(len(tweets_user) + sigma)) * sumatorio_tweet_TI
        voice_r = (1/(len(retweets_user) + sigma)) * sumatorio_retweet_TI

        command = "update (select from User where userid = '" + str(user.oRecordData['userid']) + "') set voice_t = '" + str(voice_t) + "', voice_r = '" + str(voice_r) + "'"
        client.command(command)
        print ("Voz usuario " + str(n+1))


# Metodo para calcular el parametro TWEETRANKING de los tweets (As-is::ORIGINAL)
def tweet_relevance(number_of_tweets):
    # Parametro de ajuste ALPHA
    alpha = 0.5
    limit = 10000
    iterationRID = "#-1:-1"

    iterations = math.ceil(number_of_tweets/limit)
    print("numero de iteraciones: " + str(iterations))

    for iteration_num in range(0,iterations):
        tweetlist = client.query("select from Tweet where @rid > " + iterationRID + " limit "+ str(limit))

        for tweet in tweetlist:
            user_creator = client.query("select from User where userid = '" + str(tweet.oRecordData['userid']) + "'")
            VR_score = 0
            if tweet.oRecordData['rtid'] == 0:
                try:
                    VR_score = float(user_creator[0].oRecordData['voice_t'])
                except:
                    pass
            else:
                try:
                    VR_score = float(user_creator[0].oRecordData['voice_r'])
                except:
                    pass
            users_retweeted = client.query("select expand(out('Retweeted_by')) from (select from Tweet where tid = '" + str(tweet.oRecordData['tid']) + "')")
            # users_replied = client.query("select expand(out('Replied_by')) from (select from Tweet where tid = '" + tweet.oRecordData['tid'] + "')")
            IR_score = 0
            for user in users_retweeted:
                try:
                    IR_score += float(user.oRecordData['impact'])
                except:
                    pass
            # for user in users_replied:
            #     IR_score += float(user.oRecordData['impact'])

            tweet_relevance = alpha * VR_score + (1 - alpha) * IR_score

            command = "update (select from Tweet where tid = '" + str(tweet.oRecordData['tid']) + "') set tweet_relevance = '" + str(tweet_relevance) +  "'"
            client.command(command)

        iterationRID = tweet._rid
        print ("Tweet " + str(iterationRID))




# METODO PARA REALIZAR LA FASE DE PREPARACION
def preparation_phase():
    # Calculamos el numero de usuarios y tweets que tenemos en la DB
    # number_of_users = client.query("select count(*) as count from User")
    # number_of_users = number_of_users[0].oRecordData['count']
    number_of_tweets = client.query("select count(*) as count from Tweet")
    number_of_tweets = number_of_tweets[0].oRecordData['count']
    number_of_users = 500
    user_tweetrate_score(userlist)
    influence_score(number_of_users, number_of_tweets)
    follow_relation_factor_user(number_of_users)
    impact_user(number_of_tweets)
    voice_user()
    tweet_relevance(number_of_tweets)
    user_relevance_score()
        



#EJECUCION
if __name__ == '__main__':

    client = pyorient.OrientDB("localhost", 2424)
    session_id = client.connect("root", "root")
    client.db_open("datosJ", "admin", "admin")

    preparation_phase()

    user_ranking()
    tweet_ranking()

print("::::::::FIN::::::::")