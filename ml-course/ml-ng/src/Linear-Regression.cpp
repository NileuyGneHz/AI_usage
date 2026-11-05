#include <iostream>
#include <fstream>
#include <sstream>
#include <vector>
#include <string>
#include <cmath>
#include <iomanip>

using namespace std;

// 读取数据：每行两个数，逗号分隔
void loadData(const string& filename, vector<double>& X, vector<double>& y) {
    ifstream file(filename);
    if (!file.is_open()) {
        cerr << "无法打开文件: " << filename << endl;
        exit(1);
    }
    string line;
    while (getline(file, line)) {
        stringstream ss(line);
        string token;
        getline(ss, token, ',');
        double x_val = stod(token);
        getline(ss, token, ',');
        double y_val = stod(token);
        X.push_back(x_val);
        y.push_back(y_val);
    }
    file.close();
}

// 计算代价函数 J(theta0, theta1)
double computeCost(const vector<double>& X, const vector<double>& y,
                   double theta0, double theta1) {
    int m = X.size();
    double sum = 0.0;
    for (int i = 0; i < m; ++i) {
        double h = theta0 + theta1 * X[i];   // 假设函数 h(x)
        double error = h - y[i];
        sum += error * error;
    }
    return sum / (2.0 * m);
}

// 批量梯度下降
void gradientDescent(const vector<double>& X, const vector<double>& y,
                     double& theta0, double& theta1,
                     double alpha, int iterations) {
    int m = X.size();
    for (int iter = 0; iter < iterations; ++iter) {
        double sum0 = 0.0, sum1 = 0.0;
        for (int i = 0; i < m; ++i) {
            double h = theta0 + theta1 * X[i];
            double error = h - y[i];
            sum0 += error;              // 对 theta0 的偏导累加
            sum1 += error * X[i];       // 对 theta1 的偏导累加
        }
        double dtheta0 = sum0 / m;
        double dtheta1 = sum1 / m;
        // 同时更新
        theta0 -= alpha * dtheta0;
        theta1 -= alpha * dtheta1;

        // 可选：每 100 次迭代打印一次代价
        if (iter % 100 == 0) {
            cout << "Iter " << iter
                 << ", cost = " << computeCost(X, y, theta0, theta1) << endl;
        }
    }
}

int main() {
    vector<double> X, y;
    loadData("ex1data1.txt", X, y);

    // 初始化参数
    double theta0 = 0.0;
    double theta1 = 0.0;
    double alpha = 0.01;      // 学习率
    int iterations = 1500;    // 迭代次数

    cout << fixed << setprecision(6);
    cout << "初始代价: " << computeCost(X, y, theta0, theta1) << endl;

    // 梯度下降
    gradientDescent(X, y, theta0, theta1, alpha, iterations);

    cout << "\n最终参数:\n";
    cout << "theta0 = " << theta0 << endl;
    cout << "theta1 = " << theta1 << endl;
    cout << "最终代价: " << computeCost(X, y, theta0, theta1) << endl;

    // 预测人口 3.5 万和 7 万时的利润
    double pred1 = theta0 + theta1 * 3.5;
    double pred2 = theta0 + theta1 * 7.0;
    cout << "\n预测:\n";
    cout << "人口 35,000 时利润 = " << pred1 << " 万" << endl;
    cout << "人口 70,000 时利润 = " << pred2 << " 万" << endl;

    return 0;
}