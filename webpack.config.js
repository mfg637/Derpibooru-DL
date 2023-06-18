const MiniCssExtractPlugin = require("mini-css-extract-plugin");

module.exports = {
    plugins: [new MiniCssExtractPlugin({
      filename: '[name].css',
    })],
    entry: {
        "processing-status": "./frontend-src/jsx/processing-status.jsx",
        "loading-spinner": "./frontend-src/sass/loading-spinner.sass",
    },
    module: {
        rules: [
            {
                test: /\.jsx$/,
                use: "babel-loader",
            },
            {
                test: /\.s[ac]ss$/i,
                use: [
                  MiniCssExtractPlugin.loader,
                  // Translates CSS into CommonJS
                  "css-loader",
                  // Compiles Sass to CSS
                  "sass-loader",
                ],
            },
            {
                test: /\.(svg|png|jpg|jpeg|gif)$/,
                type: "asset/inline",
            },
            {
                test: /\.css$/i,
                use: ["style-loader", "css-loader"],
            },
        ],
    },
    output: {
        path: __dirname + "/static/dist",
        filename: "[name].bundle.js",
    },
};
