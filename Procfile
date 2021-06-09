web: gunicorn main:app
heroku buildpacks:add --index 1 https://github.com/heroku-buildpack-chromedriver
heroku buildpacks:add --index 2 https://github.com/heroku-buildpack-chromedriver
heroku config:set GOOGLE_CHROME_BIN=/app/.apt/usr/bin/google_chrome
heroku config:set CHROMEDRIVER_PATH=/app/.chromedriver/bin/chromedriver
