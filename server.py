import json
import os
import traceback
import tornado.httpserver
import tornado.ioloop
import tornado.web
from tornado.gen import coroutine
from tornado.options import define, options
import tornado.escape
from tornado.escape import native_str, parse_qs_bytes
import subprocess
import firebase_admin
from firebase_admin import credentials, firestore, storage
import glob

define("port", default=8080, help="runs on the given port", type=int)


class MyAppException(tornado.web.HTTPError):
    pass


class BaseHandler(tornado.web.RequestHandler):
    def db(self):
    	cred=credentials.Certificate("./secret/agora-recording-firebase-adminsdk-21dne-7130057180.json")
    	firebase_admin.initialize_app(cred, { 'storageBucket': 'agora-recording.appspot.com' } )
    	db = firestore.client()
    	bucket = storage.bucket()
    	return bucket

    def write_error(self, status_code, **kwargs):
        self.set_header('Content-Type', 'application/json')
        if self.settings.get("serve_traceback") and "exc_info" in kwargs:
            # in debug mode, try to send a traceback
            lines = []
            for line in traceback.format_exception(*kwargs["exc_info"]):
                lines.append(line)
            self.write(json.dumps({
                        'status_code': status_code,
                        'message': self._reason,
                        'traceback': lines,
                }))
        else:
            self.write(json.dumps({
                    'status_code': status_code,
                    'message': self._reason,
                }))




class my404handler(BaseHandler):
    def get(self):
        self.set_header('Content-Type', 'application/json')
        self.write(json.dumps({
                'status_code': 404,
                'message': 'illegal call.'
        }))



class AgoraHandler(BaseHandler):
    async def post(self):
    	data = parse_qs_bytes(native_str(self.request.body), keep_blank_values=True)
    	appId, uid, channel_name, nick_name = list(map(lambda x: x[0].decode("utf-8"), [data['appid'], data['uid'], data['channel_name'], data['nick_name']]))
    	config_filename = f"configRec_{nick_name}.json"
    	sdk_path = "./Agora_Recording_SDK_for_Linux_FULL/samples/cpp/"
    	with open(os.path.join(sdk_path, config_filename), "w") as cfg:
    		cfg.write('{"Recording_Dir" : "./' + nick_name + '"}')

    	success = subprocess.run([sdk_path + 'recorder_local', "--appId", appId, "--uid", "0", "--channel", channel_name, "--appliteDir" , "Agora_Recording_SDK_for_Linux_FULL/bin/", '--idle', '4', '--audioProfile', '2', '--cfgFilePath', os.path.join(sdk_path, config_filename), "--isMixingEnabled", "1"])
    	outfile = glob.glob(str(os.path.join(os.getcwd(), nick_name) + "/*.aac"))[0]
    	# print(str(os.path.join(os.getcwd(), nick_namez o)
    	# print(outfile)
    	bucket = self.db()
    	blob = bucket.blob(nick_name + ".aac")
    	blob.upload_from_filename(outfile)
    	self.write(json.dumps({
    		'status_code': 200,
    		'message': 'everything seems to be fine',
    		'url': blob.public_url
    	}))
    		# self.write(json.dumps({
    		# 	'status_code': 500,
    		# 	'message': 'somethings wrong'
    		# }))



if __name__ == "__main__":
    options.parse_command_line()
    app = tornado.web.Application(
        handlers=[
            (r"/", AgoraHandler),
        ],
        default_handler_class = my404handler,
        debug = True,
    )
    http_server = tornado.httpserver.HTTPServer(app)
    http_server.listen(os.environ.get("PORT", options.port))
    tornado.ioloop.IOLoop.instance().start()
