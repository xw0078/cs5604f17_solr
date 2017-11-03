import json
import re
import sys
import datetime

root_elem = ["in_reply_to_status_id", "id", "favorite_count", "full_text", "retweeted", "source", "retweet_count",
             "in_reply_to_user_id_str", "possibly_sensitive", "lang", "in_reply_to_status_id_str"]

nested_elems = {
 "entities": ["user_mentions", "hashtags", "urls"],
 "user": ["verified", "followers_count", "id_str", "listed_count", "utc_offset", "statuses_count", "description", "friends_count",
          "location", "screen_name", "lang", "favourites_count", "name", "created_at", "time_zone", "protected", "profile_image_url", "contributors_enabled"],
 "place": ["full_name", "country", "place_type", "country_code", "id_str", "name"]
 }


def clear_file(filename):
	count = 0
	f = open(filename, 'r')
	out_file = open(filename+'_clean', 'w')
	for l in f:
		count += 1
		if count %1000 == 0:
			print count
		l = re.sub(r"<a href=\\\"[^,>]*>", "", l)
		l = re.sub(r"</a>", "", l)
		out_file.write(l)
	out_file.close()
	f.close()

def get_attr(obj, attr):
	resp = ''
	try:
		val = obj.get(attr, '')
		if val is None:
			val = ''
		resp = str(val)
	except:
		resp = obj.get(attr, '').encode('utf-8')
		if resp is None:
			resp = ''
	return resp

def get_column_names():
	resp = []
	resp.extend(root_elem)
	resp.append('created_at')
	resp.append('coordinates')
	resp.extend(["{0}_{1}".format('user', x) for x in nested_elems['user']])
	resp.extend(["{0}_{1}".format('place', x) for x in nested_elems['place']])
	resp.append('hashtags')
	resp.append('urls')
	resp.extend(['user_mentions_id_str', 'user_mentions_name', 'user_mentions_screen_name'])
	resp.extend(['dc_type_s', 'dc_topics_s'])
	return resp

def get_column_names_with_cf(col_names, cf_name):
	resp = ''
	for col in col_names:
		resp = resp + "{0}:{1},".format(cf_name, col)
	return resp

def get_morphlines_conf(column_names, file_name, cf_name):
	out_file = open(file_name, 'w')
	mappings = []
	skeleton = {}
	for col in column_names:
		out_file.write('{\n')
		out_file.write(' inputColumn: "{0}:{1}"\n'.format(cf_name, col))
		out_file.write(' outputField: "{0}"\n'.format(col))
		out_file.write(' type: string\n')
		out_file.write(' source: value\n')
		out_file.write('}\n')
	out_file.close()

def get_schema_file(column_names, file_name):
	out_file = open(file_name, 'w')
	for col in column_names:
		out_file.write('<field name="{0}" type="string" indexed="true" stored="true"/>\n'.format(col))
	out_file.close()


def parse_user_mentions(user_mentions):
    id_strs = None
    names = None
    screennames = None
    for e in user_mentions:
        id_str = get_attr(e, 'id_str')
        name = get_attr(e, 'name')
        screenname = get_attr(e, 'screen_name')
        if id_strs is None:
        	id_strs = id_str
        else:
            id_strs = "{0},{1}".format(id_strs,id_str)

        if names is None:
        	names = name
        else:
            names = "{0},{1}".format(names, name)

        if screennames is None:
        	screennames = screenname
        else:
            screennames = "{0},{1}".format(screennames, screenname)
    id_strs = id_strs or ''
    names = names or ''
    screennames = screennames or ''
    return "{0}\t{1}\t{2}".format(id_strs, names, screennames)

def parse_hashtags(hashtags):
    resp = None
    for e in hashtags:
        text = get_attr(e, 'text')
        if resp is None:
        	resp = text
        else:
            resp = "{0},{1}".format(resp, text)
    resp = resp or ''
    return resp

def parse_urls(urls):
    resp = None
    for e in urls:
        display_url = get_attr(e, 'display_url')
        if resp is None:
        	resp = display_url
        else:
            resp = "{0},{1}".format(resp, display_url)
    resp = resp or ''
    return resp

def parse_coordinates(coordinates):
	resp = '0.0,0.0'
	if not coordinates:
		return resp
	if coordinates['type'] == 'Point':
		resp = "{0},{1}".format(coordinates['coordinates'][1], coordinates['coordinates'][0])
	return resp

def parse_user_info(users_info):
	resp = None
	users_info = users_info or {}

	for attr in nested_elems['user']:
		value = get_attr(users_info, attr)
		if attr == 'created_at':
			value = parse_date(value)
		if resp is None:
			resp = value
		else:
			resp = "{0}\t{1}".format(resp, value)
	resp = resp or ''
	return resp

def parse_place(place_info):
	resp = None
	place_info = place_info or {}
	for attr in nested_elems['place']:
		if resp is None:
			resp = get_attr(place_info, attr)
		else:
			resp = "{0}\t{1}".format(resp, get_attr(place_info, attr))
	resp = resp or ''
	return resp

def parse_eclipse_data(file_name):
	in_file = open(file_name, 'r')
	count = 0
	out_file = open(file_name+'.tsv', 'w')
	for l in in_file:
		count += 1
		if count %1000 == 0:
			print count
		out_line = None
		l = l.replace('\\r', ' ')
		l = l.replace('\\n', ' ')

		try:
 			obj = json.loads(l)
 		except:
 			continue
		for attr in root_elem:
			if out_line is None:
				out_line = get_attr(obj, attr)
			else:
				try:
					out_line = "{0}\t{1}".format(out_line, get_attr(obj, attr))
				except:
					out_line = "{0}\t{1}".format(out_line, get_attr(obj, attr))
        	out_line = "{0}\t{1}".format(out_line, parse_date(get_attr(obj, 'created_at')))
		out_line = "{0}\t{1}".format(out_line, parse_coordinates(obj.get('coordinates', None)))
		out_line = "{0}\t{1}".format(out_line, parse_user_info(obj.get('user', {})))
		out_line = "{0}\t{1}".format(out_line, parse_place(obj.get('place', {})))
		out_line = "{0}\t{1}".format(out_line, parse_hashtags(obj.get('entities').get('hashtags', [])))
		out_line = "{0}\t{1}".format(out_line, parse_urls(obj.get('entities').get('urls', [])))
		out_line = "{0}\t{1}".format(out_line, parse_user_mentions(obj.get('entities').get('user_mentions', [])))
		out_line = "{0}\t{1}\t{2}".format(out_line, 'tweet', 'eclipse')
		out_file.write(out_line + '\n')
	out_file.close()
	in_file.close()


def parse_date(date_str):
	d_obj = datetime.datetime.strptime(date_str, '%a %b %d %H:%M:%S +0000 %Y')
	return str(int(total_seconds(d_obj - datetime.datetime(1970, 1, 1))))

def print_tsv(file_name):
	f = open(file_name, 'r')
	for l in f:
		print len(l.split('\t')), l.split('\t')
		raw_input()

def total_seconds(dt):
    # Keep backward compatibility with Python 2.6 which doesn't have
    # this method
    if hasattr(datetime, 'total_seconds'):
        return dt.total_seconds()
    else:
        return (dt.microseconds + (dt.seconds + dt.days * 24 * 3600) * 10**6) / 10**6

if __name__ == '__main__':
	file_name = sys.argv[1]
	parse_eclipse_data(file_name)
	#col_names = get_column_names()
	#print len(col_names)
	#get_morphlines_conf(col_names, 'morph.conf', 'tweet')
        #get_schema_file(col_names, 'schema')
	#print get_column_names_with_cf(col_names, 'tweet')
	#print_tsv(file_name)
	# clear_file(file_name)
