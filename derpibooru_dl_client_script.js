// ==UserScript==
// @name        derpibooru_dl_client_script
// @namespace   Violentmonkey Scripts
// @match       https://derpibooru.org/
// @match       https://derpibooru.org/images
// @match       https://derpibooru.org/search
// @connect     localhost:5757
// @grant       GM.xmlHttpRequest
// @version     1.0
// @author      mfg637
// @description 12.03.2021, 13:25:40
// ==/UserScript==

waiting_dl_button = null

function dl_button_click_handler(event){
  console.log(this.data);
  console.log(JSON.stringify(this.data));
  GM.xmlHttpRequest({
    method: "POST",
    data: JSON.stringify(this.data),
    url: `http://localhost:5757`,
    onload: function(response) {
      if (response.responseText === "OK"){
        event.target.style.backgroundColor = "green";
        event.target.style.color = 'white';
        console.log(response.responseText);
      }else
        alert(response.responseText);
    }
  });
  return false;
}

function image_handler(image_wrapper){
  if (!(image_wrapper instanceof Element)){return;}
  data_wrapper = image_wrapper.getElementsByClassName('image-container')[0];
  let raw_data = data_wrapper.dataset, data = {};
  for (let key in raw_data){data[key]=raw_data[key];}
  data.representations=JSON.parse(data.uris);
  delete data.uris;
  let dl_button = document.createElement('a');
  dl_button.innerText='dl';
  dl_button.data = data;
  dl_button.href = 'http://localhost:5757';
  dl_button.onclick = dl_button_click_handler;
  dl_button.style.fontWeight = 'Bold';
  image_wrapper.getElementsByClassName('media-box__header')[0].appendChild(dl_button);
}

image_wrappers = document.getElementsByClassName('media-box');
for (let i in image_wrappers){image_handler(image_wrappers[i]);}
