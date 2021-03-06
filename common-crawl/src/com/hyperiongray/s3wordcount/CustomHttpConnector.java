package com.hyperiongray.s3wordcount;

import java.io.IOException;
import java.io.InputStream;
import java.net.URL;
import java.net.URLConnection;

import org.apache.commons.io.IOUtils;

public class CustomHttpConnector {

	public static final String charset ="UTF-8";
	
	public String getContent(String url){
		URLConnection connection;
		InputStream inputStream;
		String content="";
		try {
			connection = new URL(url).openConnection();
			connection.setRequestProperty("Accept-Charset", charset );
			inputStream = connection.getInputStream();
			content = IOUtils.toString(inputStream, charset);
		} catch (IOException e) {
			// TODO Auto-generated catch block
			e.printStackTrace();
		}
		return content;
	}
}
