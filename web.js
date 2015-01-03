var express = require('express');
var app = express();
var request = require('request');
var fs = require('fs');
var geolib = require('geolib');

var mainHTML = fs.readFileSync('./html/main.html').toString();

function predicatBy(prop){
   return function(a,b){
      if( a[prop] > b[prop]){
          return 1;
      }else if( a[prop] < b[prop] ){
          return -1;
      }
      return 0;
   }
}

function syntaxHighlight(json) {
        if (typeof json != 'string') {
                     json = JSON.stringify(json, undefined, 2);
                }
                json = json.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
                return json.replace(/("(\\u[a-zA-Z0-9]{4}|\\[^u]|[^\\"])*"(\s*:)?|\b(true|false|null)\b|-?\d+(?:\.\d*)?(?:[eE][+\-]?\d+)?)/g, function (match) {
                    var cls = 'number';
                    if (/^"/.test(match)) {
                        if (/:$/.test(match)) {
                            cls = 'key';
                        } else {
                            cls = 'string';
                        }
                    } else if (/true|false/.test(match)) {
                        cls = 'boolean';
                    } else if (/null/.test(match)) {
                        cls = 'null';
                    }
                    return '<span class="' + cls + '">' + match + '</span>';
                });
}

app.get('/tier2s.:format(json|html)', function (req, res) {
  if(req.query.geoorder !== undefined && req.query.geoorder == "true"){
  	var ipAddr = req.headers['X-Real-IP'] || req.headers['x-real-ip'] || req.connection.remoteAddress;
	request({url: "http://geoip.nekudo.com/api/"+ipAddr}, function index(error, response, body) {
		try{
			var respjson = JSON.parse(body)

			if(respjson.type == "error") {
				var respjson = {"location":{"latitude":0,"longitude":0}}
			}
		}catch(e){
			var respjson = {"location":{"latitude":0,"longitude":0}}
		}
		
		var latitude = respjson.location.latitude
		var longitude = respjson.location.longitude
		
		console.log(respjson)

		fs.readFile('data/tier2s.json', 'utf8', function (err,data) {
		  if (err) {
		    return console.log(err);
		  }
		  var tier2json = JSON.parse(data);

			for(i in tier2json.data){
				tier2json.data[i].distance = geolib.getDistance(
	    			{latitude: latitude, longitude: longitude}, 
	    			{latitude: tier2json.data[i].coords.lat, longitude: tier2json.data[i].coords.lng}
				);
			}

			tier2json.data.sort(predicatBy("distance"));

			if(req.param("format") == "json"){
        res.header('Access-Control-Allow-Origin', '*');
				res.json(tier2json)
			}else{
				res.send(mainHTML.replace("{{title}}","Public Access (Tier-2) DNS Servers - sorted by distance from "+ipAddr).replace("{{content}}" ,syntaxHighlight(tier2json)))
			}

		});
	})

  }else{
	fs.readFile('data/tier2s.json', function(err, data) {
		if(req.param("format") == "json"){
      res.header('Access-Control-Allow-Origin', '*');
			res.json(JSON.parse(data));
		}else{
			res.send(mainHTML.replace("{{title}}","Public Access (Tier-2) DNS Servers").replace("{{content}}" ,syntaxHighlight(JSON.parse(data))))
		}
	});
  }
})

app.get('/tier1s.:format(json|html)', function (req, res) {
	fs.readFile('data/tier1s.json', function(err, data) {
		if(req.param("format") == "json"){
      res.header('Access-Control-Allow-Origin', '*');
			res.json(JSON.parse(data));
		}else{
			res.send(mainHTML.replace("{{title}}","Master Pool (Tier 1) DNS Servers").replace("{{content}}" ,syntaxHighlight(JSON.parse(data))))
		}
	});
})

app.get('/tlds.:format(json|html)', function (req, res) {
	fs.readFile('data/tlds.json', function(err, data) {
		if(req.param("format") == "json"){
      res.header('Access-Control-Allow-Origin', '*');
			res.json(JSON.parse(data));
		}else{
			res.send(mainHTML.replace("{{title}}","OpenNIC Top-Level Domains").replace("{{content}}" ,syntaxHighlight(JSON.parse(data))))
		}
	});
})

app.get('/newnationstlds.:format(json|html)', function (req, res) {
	fs.readFile('data/newnationstlds.json', function(err, data) {
		if(req.param("format") == "json"){
      res.header('Access-Control-Allow-Origin', '*');
			res.json(JSON.parse(data));
		}else{
			res.send(mainHTML.replace("{{title}}","New Nationstlds Top-Level Domains").replace("{{content}}" ,syntaxHighlight(JSON.parse(data))))
		}
	});
})

app.get('/', function (req, res) {
  res.sendFile("html/index.html", { root: __dirname })
})

app.get('/robots.txt', function (req, res) {
  res.sendFile("html/robots.txt", { root: __dirname })
})

app.get('/robots.txt', function (req, res) {
  res.sendFile("html/robots.txt", { root: __dirname })
})

app.use(function (err, req, res, next) {
  console.error(err.stack);
  res.status(500).sendFile('html/500.html', { root: __dirname });
});

app.use(function (req, res) {
  res.status(404).sendFile('html/404.html', { root: __dirname });
});

app.listen(parseInt(process.argv[2]) || 3000);